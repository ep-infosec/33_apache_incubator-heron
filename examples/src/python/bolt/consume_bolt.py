#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.


'''module for example bolt: Consume Bolt'''
from heronpy.api.bolt.bolt import Bolt

# pylint: disable=unused-argument
class ConsumeBolt(Bolt):
  def initialize(self, config, context):
    self.logger.info("In prepare() of ConsumerBolt")
    self.total = 0

  def process(self, tup):
    self.total += 1

  def process_tick(self, tup):
    self.log("Got tick tuple!")
    self.log(f"Total received data tuple: {self.total}")
