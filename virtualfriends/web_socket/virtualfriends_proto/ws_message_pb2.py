# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: ws_message.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10ws_message.proto\x12\x14virtualfriends_proto\"\xa0\x01\n\tVfRequest\x12\x31\n\x04\x65\x63ho\x18\x02 \x01(\x0b\x32!.virtualfriends_proto.EchoRequestH\x00\x12O\n\x14stream_reply_message\x18\x06 \x01(\x0b\x32/.virtualfriends_proto.StreamReplyMessageRequestH\x00\x42\t\n\x07requestJ\x04\x08\x01\x10\x02\"\xd0\x01\n\nVfResponse\x12\x30\n\x05\x65rror\x18\x01 \x01(\x0b\x32!.virtualfriends_proto.CustomError\x12\x32\n\x04\x65\x63ho\x18\x02 \x01(\x0b\x32\".virtualfriends_proto.EchoResponseH\x00\x12P\n\x14stream_reply_message\x18\x06 \x01(\x0b\x32\x30.virtualfriends_proto.StreamReplyMessageResponseH\x00\x42\n\n\x08response\"$\n\x0b\x43ustomError\x12\x15\n\rerror_message\x18\x01 \x01(\t\"\x1b\n\x0b\x45\x63hoRequest\x12\x0c\n\x04text\x18\x01 \x01(\t\"\x1c\n\x0c\x45\x63hoResponse\x12\x0c\n\x04text\x18\x01 \x01(\t\"\xc9\x01\n\x19StreamReplyMessageRequest\x12\x16\n\x0e\x63haracter_name\x18\x01 \x01(\t\x12\x15\n\rjson_messages\x18\x02 \x03(\t\x12\r\n\x03wav\x18\x03 \x01(\x0cH\x00\x12\x0e\n\x04text\x18\x06 \x01(\tH\x00\x12\x12\n\nsession_id\x18\x04 \x01(\x03\x12\x37\n\x0cvoice_config\x18\x05 \x01(\x0e\x32!.virtualfriends_proto.VoiceConfigB\x11\n\x0f\x63urrent_message\"\xbd\x01\n\x1aStreamReplyMessageResponse\x12\x15\n\rreply_message\x18\x01 \x01(\t\x12\x0e\n\x06\x61\x63tion\x18\x02 \x01(\t\x12\x11\n\tsentiment\x18\x03 \x01(\t\x12\x11\n\treply_wav\x18\x04 \x01(\x0c\x12\x18\n\x10transcribed_text\x18\x05 \x01(\t\x12\x12\n\nsession_id\x18\x06 \x01(\x03\x12\x13\n\x0b\x63hunk_index\x18\x07 \x01(\x05\x12\x0f\n\x07is_stop\x18\x08 \x01(\x08*\x95\x01\n\x0bVoiceConfig\x12\x17\n\x13VoiceConfig_Invalid\x10\x00\x12\x1a\n\x16VoiceConfig_NormalMale\x10\x01\x12\x1d\n\x19VoiceConfig_NormalFemale1\x10\x02\x12\x1d\n\x19VoiceConfig_NormalFemale2\x10\x03\x12\x13\n\x0fVoiceConfig_Orc\x10\x04\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'ws_message_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_VOICECONFIG']._serialized_start=910
  _globals['_VOICECONFIG']._serialized_end=1059
  _globals['_VFREQUEST']._serialized_start=43
  _globals['_VFREQUEST']._serialized_end=203
  _globals['_VFRESPONSE']._serialized_start=206
  _globals['_VFRESPONSE']._serialized_end=414
  _globals['_CUSTOMERROR']._serialized_start=416
  _globals['_CUSTOMERROR']._serialized_end=452
  _globals['_ECHOREQUEST']._serialized_start=454
  _globals['_ECHOREQUEST']._serialized_end=481
  _globals['_ECHORESPONSE']._serialized_start=483
  _globals['_ECHORESPONSE']._serialized_end=511
  _globals['_STREAMREPLYMESSAGEREQUEST']._serialized_start=514
  _globals['_STREAMREPLYMESSAGEREQUEST']._serialized_end=715
  _globals['_STREAMREPLYMESSAGERESPONSE']._serialized_start=718
  _globals['_STREAMREPLYMESSAGERESPONSE']._serialized_end=907
# @@protoc_insertion_point(module_scope)
