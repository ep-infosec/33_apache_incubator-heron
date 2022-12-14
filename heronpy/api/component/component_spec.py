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

'''component_spec.py'''
import uuid

from heronpy.api.serializer import default_serializer
from heronpy.api.api_constants import TOPOLOGY_COMPONENT_PARALLELISM
from heronpy.proto import topology_pb2

from heronpy.api.stream import Stream, Grouping

# pylint: disable=too-many-instance-attributes
class HeronComponentSpec:
  """Class to specify the information and location of components in a topology

  This class is generated by the ``spec()`` method of Spout and Bolt class and
  specifies how this component is located in the topology and how it is connected to
  the other components. This class also retains the Python class path of the component,
  so pex_loader can load the component appropriately.
  """
  def __init__(self, name, python_class_path, is_spout, par,
               inputs=None, outputs=None, config=None):
    self._sanitize_args(name, python_class_path, is_spout, par)

    self.name = name
    self.python_class_path = python_class_path
    self.is_spout = is_spout
    self.parallelism = par

    # inputs, outputs, config will be sanitized later
    self.inputs = inputs
    self.outputs = outputs
    self.custom_config = config

    # This is used for identification, especially when name is not specified by argument
    # Note that ``self.name`` might not be available until it is set by TopologyType metaclass
    # so this is necessary for identification purposes. Used mainly by GlobalStreamId.
    self.uuid = str(uuid.uuid4())

  @staticmethod
  def _sanitize_args(name, py_class_path, is_spout, par):
    # name can be None at the time this spec is initialized
    assert name is None or isinstance(name, str)
    assert isinstance(py_class_path, str)
    assert isinstance(is_spout, bool)
    assert isinstance(par, int) and par > 0

  def get_protobuf(self):
    """Returns protobuf message (Spout or Bolt) of this component"""
    if self.is_spout:
      return self._get_spout()
    return self._get_bolt()

  def _get_spout(self):
    """Returns Spout protobuf message"""
    spout = topology_pb2.Spout()
    spout.comp.CopyFrom(self._get_base_component())

    # Add output streams
    self._add_out_streams(spout)
    return spout

  def _get_bolt(self):
    """Returns Bolt protobuf message"""
    bolt = topology_pb2.Bolt()
    bolt.comp.CopyFrom(self._get_base_component())

    # Add streams
    self._add_in_streams(bolt)
    self._add_out_streams(bolt)
    return bolt

  def _get_base_component(self):
    """Returns Component protobuf message"""
    comp = topology_pb2.Component()
    comp.name = self.name
    comp.spec = topology_pb2.ComponentObjectSpec.Value("PYTHON_CLASS_NAME")
    comp.class_name = self.python_class_path
    comp.config.CopyFrom(self._get_comp_config())
    return comp

  def _get_comp_config(self):
    """Returns component-specific Config protobuf message

    It first adds ``topology.component.parallelism``, and is overriden by
    a user-defined component-specific configuration, specified by spec().
    """
    proto_config = topology_pb2.Config()

    # first add parallelism
    key = proto_config.kvs.add()
    key.key = TOPOLOGY_COMPONENT_PARALLELISM
    key.value = str(self.parallelism)
    key.type = topology_pb2.ConfigValueType.Value("STRING_VALUE")

    # iterate through self.custom_config
    if self.custom_config is not None:
      sanitized = self._sanitize_config(self.custom_config)
      for key, value in list(sanitized.items()):
        if isinstance(value, str):
          kvs = proto_config.kvs.add()
          kvs.key = key
          kvs.value = value
          kvs.type = topology_pb2.ConfigValueType.Value("STRING_VALUE")
        else:
          # need to serialize
          kvs = proto_config.kvs.add()
          kvs.key = key
          kvs.serialized_value = default_serializer.serialize(value)
          kvs.type = topology_pb2.ConfigValueType.Value("PYTHON_SERIALIZED_VALUE")

    return proto_config

  @staticmethod
  def _sanitize_config(custom_config):
    """Checks whether ``custom_config`` is sane and returns a sanitized dict <str -> (str|object)>

    It checks if keys are all strings and sanitizes values of a given dictionary as follows:

    - If string, number or boolean is given as a value, it is converted to string.
      For string and number (int, float), it is converted to string by a built-in ``str()`` method.
      For a boolean value, ``True`` is converted to "true" instead of "True", and ``False`` is
      converted to "false" instead of "False", in order to keep the consistency with
      Java configuration.

    - If neither of the above is given as a value, it is inserted into the sanitized dict as it is.
      These values will need to be serialized before adding to a protobuf message.
    """
    if not isinstance(custom_config, dict):
      raise TypeError("Component-specific configuration must be "\
        f"given as a dict type, given: {str(type(custom_config))}")
    sanitized = {}
    for key, value in list(custom_config.items()):
      if not isinstance(key, str):
        raise TypeError("Key for component-specific configuration "\
          f"must be string, given: {str(type(key))}:{str(key)}")

      if isinstance(value, bool):
        sanitized[key] = "true" if value else "false"
      elif isinstance(value, (str, int, float)):
        sanitized[key] = str(value)
      else:
        sanitized[key] = value

    return sanitized

  def _add_in_streams(self, bolt):
    """Adds inputs to a given protobuf Bolt message"""
    if self.inputs is None:
      return
    # sanitize inputs and get a map <GlobalStreamId -> Grouping>
    input_dict = self._sanitize_inputs()

    for global_streamid, gtype in list(input_dict.items()):
      in_stream = bolt.inputs.add()
      in_stream.stream.CopyFrom(self._get_stream_id(global_streamid.component_id,
                                                    global_streamid.stream_id))
      if isinstance(gtype, Grouping.FIELDS):
        # it's a field grouping
        in_stream.gtype = gtype.gtype
        in_stream.grouping_fields.CopyFrom(self._get_stream_schema(gtype.fields))
      elif isinstance(gtype, Grouping.CUSTOM):
        # it's a custom grouping
        in_stream.gtype = gtype.gtype
        in_stream.custom_grouping_object = gtype.python_serialized
        in_stream.type = topology_pb2.CustomGroupingObjectType.Value("PYTHON_OBJECT")
      else:
        in_stream.gtype = gtype

  # pylint: disable=too-many-branches
  def _sanitize_inputs(self):
    """Sanitizes input fields and returns a map <GlobalStreamId -> Grouping>"""
    ret = {}
    if self.inputs is None:
      return None

    if isinstance(self.inputs, dict):
      # inputs are dictionary, must be either <HeronComponentSpec -> Grouping> or
      # <GlobalStreamId -> Grouping>
      for key, grouping in list(self.inputs.items()):
        if not Grouping.is_grouping_sane(grouping):
          raise ValueError('A given grouping is not supported')
        if isinstance(key, HeronComponentSpec):
          # use default streamid
          if key.name is None:
            # should not happen as TopologyType metaclass sets name attribute
            # before calling this method
            raise RuntimeError("In _sanitize_inputs(): HeronComponentSpec doesn't have a name")
          global_streamid = GlobalStreamId(key.name, Stream.DEFAULT_STREAM_ID)
          ret[global_streamid] = grouping
        elif isinstance(key, GlobalStreamId):
          ret[key] = grouping
        else:
          raise ValueError(f"{str(key)} is not supported as a key to inputs")
    elif isinstance(self.inputs, (list, tuple)):
      # inputs are lists, must be either a list of HeronComponentSpec or GlobalStreamId
      # will use SHUFFLE grouping
      for input_obj in self.inputs:
        if isinstance(input_obj, HeronComponentSpec):
          if input_obj.name is None:
            # should not happen as TopologyType metaclass sets name attribute
            # before calling this method
            raise RuntimeError("In _sanitize_inputs(): HeronComponentSpec doesn't have a name")
          global_streamid = GlobalStreamId(input_obj.name, Stream.DEFAULT_STREAM_ID)
          ret[global_streamid] = Grouping.SHUFFLE
        elif isinstance(input_obj, GlobalStreamId):
          ret[input_obj] = Grouping.SHUFFLE
        else:
          raise ValueError(f"{str(input_obj)} is not supported as an input")
    else:
      raise TypeError(f"Inputs must be a list, dict, or None, given: {str(self.inputs)}")

    return ret

  def _add_out_streams(self, spbl):
    """Adds outputs to a given protobuf Bolt or Spout message"""
    if self.outputs is None:
      return

    # sanitize outputs and get a map <stream_id -> out fields>
    output_map = self._sanitize_outputs()

    for stream_id, out_fields in list(output_map.items()):
      out_stream = spbl.outputs.add()
      out_stream.stream.CopyFrom(self._get_stream_id(self.name, stream_id))
      out_stream.schema.CopyFrom(self._get_stream_schema(out_fields))

  def _sanitize_outputs(self):
    """Sanitizes output fields and returns a map <stream_id -> list of output fields>"""
    ret = {}
    if self.outputs is None:
      return None

    if not isinstance(self.outputs, (list, tuple)):
      raise TypeError("Argument to outputs must be either "\
        f"list or tuple, given: {str(type(self.outputs))}")

    for output in self.outputs:
      if not isinstance(output, (str, Stream)):
        raise TypeError("Outputs must be a list of strings "\
          f"or Streams, given: {str(output)}")

      if isinstance(output, str):
        # it's a default stream
        if Stream.DEFAULT_STREAM_ID not in ret:
          ret[Stream.DEFAULT_STREAM_ID] = []
        ret[Stream.DEFAULT_STREAM_ID].append(output)
      else:
        # output is a Stream object
        if output.stream_id == Stream.DEFAULT_STREAM_ID and Stream.DEFAULT_STREAM_ID in ret:
          # some default stream fields are already in there
          ret[Stream.DEFAULT_STREAM_ID].extend(output.fields)
        else:
          ret[output.stream_id] = output.fields
    return ret

  def get_out_streamids(self):
    """Returns a set of output stream ids registered for this component"""
    if self.outputs is None:
      return set()

    if not isinstance(self.outputs, (list, tuple)):
      raise TypeError("Argument to outputs must be either "\
        f"list or tuple, given: {str(type(self.outputs))}")
    ret_lst = []
    for output in self.outputs:
      if not isinstance(output, (str, Stream)):
        raise TypeError(f"Outputs must be a list of strings or Streams, given: {str(output)}")
      ret_lst.append(Stream.DEFAULT_STREAM_ID if isinstance(output, str) else output.stream_id)
    return set(ret_lst)

  def __getitem__(self, stream_id):
    """Get GlobalStreamId for a given stream_id"""
    if stream_id not in self.get_out_streamids():
      raise ValueError(f"A given stream id does not exist on this component: {stream_id}")

    component_id = self.name or self
    return GlobalStreamId(componentId=component_id, streamId=stream_id)

  @staticmethod
  def _get_stream_id(comp_name, stream_id):
    """Returns a StreamId protobuf message"""
    proto_stream_id = topology_pb2.StreamId()
    proto_stream_id.id = stream_id
    proto_stream_id.component_name = comp_name
    return proto_stream_id

  @staticmethod
  def _get_stream_schema(fields):
    """Returns a StreamSchema protobuf message"""
    stream_schema = topology_pb2.StreamSchema()
    for field in fields:
      key = stream_schema.keys.add()
      key.key = field
      key.type = topology_pb2.Type.Value("OBJECT")

    return stream_schema

class GlobalStreamId:
  """Wrapper class to define stream_id and its component name

  Constructor method is compatible with StreamParse's GlobalStreamId class, although
  the object itself is completely different, as Heron does not use Thrift.
  This is mainly used for declaring input fields when defining a topology, and internally
  in HeronComponentSpec.

  Note that topology writers never have to create an instance of this class by themselves,
  as it is created automatically.
  """
  def __init__(self, componentId, streamId):
    """
    :type componentId: str or HeronComponentSpec
    :param componentId: component id from which the tuple is emitted, or HeronComponentSpec object.
    :type streamId: str
    :param streamId: stream id through which the tuple is transmitted
    """
    if not isinstance(componentId, (str, HeronComponentSpec)):
      raise TypeError('GlobalStreamId: componentId must be either string or HeronComponentSpec')
    if not isinstance(streamId, str):
      raise TypeError('GlobalStreamId: streamId must be string type')

    self._component_id = componentId
    self.stream_id = streamId

  @property
  def component_id(self):
    """Returns component_id of this GlobalStreamId

    Note that if HeronComponentSpec is specified as componentId and its name is not yet
    available (i.e. when ``name`` argument was not given in ``spec()`` method in Bolt or Spout),
    this property returns a message with uuid. However, this is provided only for safety
    with __eq__(), __str__(), and __hash__() methods, and not meant to be called explicitly
    before TopologyType class finally sets the name attribute of HeronComponentSpec.
    """
    if isinstance(self._component_id, HeronComponentSpec):
      if self._component_id.name is None:
        # HeronComponentSpec instance's name attribute might not be available until
        # TopologyType metaclass finally sets it. This statement is to support __eq__(),
        # __hash__() and __str__() methods with safety, as raising Exception is not
        # appropriate this case.
        return f"<No name available for HeronComponentSpec yet, uuid: {self._component_id.uuid}>"
      return self._component_id.name
    if isinstance(self._component_id, str):
      return self._component_id
    raise ValueError("Component Id for this GlobalStreamId is not "\
                    f"properly set: <{str(type(self._component_id))}:{str(self._component_id)}>")

  def __eq__(self, other):
    return hasattr(other, 'component_id') and self.component_id == other.component_id \
           and hasattr(other, 'stream_id') and self.stream_id == other.stream_id

  def __hash__(self):
    return hash(self.__str__())

  def __str__(self):
    return f"{self.component_id}:{self.stream_id}"
