# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Saeed Rasooli <saeed.gnu@gmail.com> (ilius)
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/lgpl.txt>.
# Also avalable in /usr/share/common-licenses/LGPL on Debian systems
# or /usr/share/licenses/common/LGPL/license.txt on ArchLinux

import sys
from math import log

sys.path.append('/starcal2')

from scal2.time_utils import *
from scal2.core import to_jd, jd_to, convert, DATE_GREG, floatJdEncode

J2000 = to_jd(2000, 1, 1, DATE_GREG)

#maxLevel = 1
#minLevel = 1

class Node:
    def __init__(self, base, level, offset, rightOri):
        #global maxLevel, minLevel
        self.base = base ## 8 or 16 is better
        self.level = level ## base ** level is the mathematical scope of the node (with its children)
        #if level > maxLevel:
        #    maxLevel = level
        #    print 'maxLevel =', level
        #if level < minLevel:
        #    minLevel = level
        #    print 'minLevel =', level
        self.offset = offset ## in days
        self.rightOri = rightOri ## FIXME
        self.clear()
    def clear(self):
        self.children = {} ## possible keys are 0 to base-1 for right node, or -(base-1) to 0 for left node
        self.events = [] ## list of tuples (rel_start, rel_end, event_id)
    def getScope(self):
        if self.rightOri:
            return self.offset, self.offset + self.base ** self.level
        else:
            return self.offset - self.base ** self.level, self.offset
    def inScope(self, tm):
        s0, s1 = self.getScope()
        return s0 <= tm <= s1
    def overlapScope(self, t0, t1):
        s0, s1 = self.getScope()
        return overlaps(t0, t1, s0, s1)
    def getEvents(self, t0, t1):## t0 < t1
        '''
            returns a list of (ev_t0, ev_t1, ev_id) s
        '''
        ## t0 and t1 are absolute. not relative to the self.offset
        if not self.overlapScope(t0, t1):
            return []
        events = []
        for ev_rt0, ev_rt1, ev_id in self.events:
            ev_t0 = ev_rt0 + self.offset
            ev_t1 = ev_rt1 + self.offset
            if overlaps(t0, t1, ev_t0, ev_t1):
                ## events.append((ev_t0, ev_t1, ev_id))
                events.append((max(t0, ev_t0), min(t1, ev_t1), ev_id))
        for child in self.children.values():
            events += child.getEvents(t0, t1)
        return events
    def getChild(self, tm):
        if not self.inScope(tm):
            raise RuntimeError('Node.getChild: Out of scope (level=%s, offset=%s, rightOri=%s'%
                (self.level, self.offset, self.rightOri))
        dt = self.base ** (self.level - 1)
        index = int((tm-self.offset) // dt)
        try:
            return self.children[index]
        except KeyError:
            child = self.children[index] = Node(
                self.base,
                self.level-1,
                self.offset + index * self.base ** (self.level - 1),
                self.rightOri,
            )
            return child
    def newParent(self):
        parent = Node(
             self.base,
             self.level+1,
             self.offset,
             self.rightOri,
        )
        parent.children[0] = self
        return parent

class CenterNode:
    def __init__(self, base=4, offset=J2000):
        ## base 4 and 8 are the best (about speed of both addEvent and getEvents)
        self.base = base
        self.offset = offset
        self.clear()
    def clear(self):
        self.right = Node(self.base, 1, self.offset, True)
        self.left = Node(self.base, 1, self.offset, False)
        self.byEvent = {}
    def getEvents(self, t0, t1):
        if self.offset <= t0:
            return self.right.getEvents(t0, t1)
        elif t0 < self.offset < t1:
            return self.left.getEvents(t0, self.offset) + self.right.getEvents(self.offset, t1)
        elif t1 <= self.offset:
            return self.left.getEvents(t0, t1)
        else:
            raise RuntimeError
    def addEvent(self, t0, t1, ev_id):
        if self.offset <= t0:
            isRight = True
            node = self.right
        elif t0 < self.offset < t1:
            self.addEvent(t0, self.offset, ev_id)
            self.addEvent(self.offset, t1, ev_id)
            return
        elif t1 <= self.offset:
            isRight = False
            node = self.left
        else:
            raise RuntimeError
        ########
        while True:
            s0, s1 = node.getScope()
            if s0 <= t0 < s1 and s0 < t1 <= s1:
                break
            node = node.newParent()
        ## now `node` is the root node
        if isRight:
            self.right = node
        else:
            self.left = node
        while True:
            child = node.getChild(t0)
            if child.inScope(t1):
                node = child
            else:
                break
        ## now `node` is the node that event should be placed in
        ev_tuple = (t0-node.offset, t1-node.offset, ev_id)
        node.events.append(ev_tuple)
        try:
            self.byEvent[ev_id].append((node, ev_tuple))
        except KeyError:
            self.byEvent[ev_id] = [(node, ev_tuple)]
    def delEvent(self, ev_id):
        try:
            refList = self.byEvent.pop(ev_id)
        except KeyError:
            return
        for node, ev_tuple in refList:
            try:
                node.events.remove(ev_tuple)
            except ValueError:
                continue
            #if not node.events:
            #   node.parent.removeChild(node)


#if __name__=='__main__':
#    from scal2 import ui
#    import time
#    ui.eventGroups.load()
#    for group in ui.eventGroups:
#        t0 = time.time()
#        group.updateOccurrenceNode()
#        print time.time()-t0, group.title
    


