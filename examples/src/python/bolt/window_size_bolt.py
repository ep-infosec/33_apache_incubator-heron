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

"""module for example bolt: WindowSizeBolt"""
from heronpy.api.bolt.window_bolt import SlidingWindowBolt

# pylint: disable=unused-argument
class WindowSizeBolt(SlidingWindowBolt):
  """WindowSizeBolt
     A bolt that calculates the average batch size of window"""

  def initialize(self, config, context):
    super().initialize(config, context)
    self.numerator = 0.0
    self.denominator = 0.0

  def processWindow(self, window_info, tuples):
    self.numerator += len(tuples)
    self.denominator += 1
    self.logger.info(f"The current average is {(self.numerator / self.denominator)}")
