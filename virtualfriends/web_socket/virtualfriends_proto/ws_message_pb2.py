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




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10ws_message.proto\x12\x14virtualfriends_proto\"\xc3\x03\n\tVfRequest\x12\x31\n\x04\x65\x63ho\x18\x02 \x01(\x0b\x32!.virtualfriends_proto.EchoRequestH\x00\x12O\n\x14stream_reply_message\x18\x06 \x01(\x0b\x32/.virtualfriends_proto.StreamReplyMessageRequestH\x00\x12Q\n\x15\x64ownload_asset_bundle\x18\x07 \x01(\x0b\x32\x30.virtualfriends_proto.DownloadAssetBundleRequestH\x00\x12\x42\n\rdownload_blob\x18\t \x01(\x0b\x32).virtualfriends_proto.DownloadBlobRequestH\x00\x12\x42\n\rget_character\x18\r \x01(\x0b\x32).virtualfriends_proto.GetCharacterRequestH\x00\x12\x0f\n\x07ip_addr\x18\x08 \x01(\t\x12\x10\n\x08username\x18\n \x01(\t\x12\x0f\n\x07user_id\x18\x0b \x01(\t\x12\x12\n\nsession_id\x18\x0c \x01(\tB\t\n\x07requestJ\x04\x08\x01\x10\x02\"\xae\x03\n\nVfResponse\x12\x30\n\x05\x65rror\x18\x01 \x01(\x0b\x32!.virtualfriends_proto.CustomError\x12\x32\n\x04\x65\x63ho\x18\x02 \x01(\x0b\x32\".virtualfriends_proto.EchoResponseH\x00\x12P\n\x14stream_reply_message\x18\x06 \x01(\x0b\x32\x30.virtualfriends_proto.StreamReplyMessageResponseH\x00\x12R\n\x15\x64ownload_asset_bundle\x18\x07 \x01(\x0b\x32\x31.virtualfriends_proto.DownloadAssetBundleResponseH\x00\x12\x43\n\rdownload_blob\x18\x08 \x01(\x0b\x32*.virtualfriends_proto.DownloadBlobResponseH\x00\x12\x43\n\rget_character\x18\t \x01(\x0b\x32*.virtualfriends_proto.GetCharacterResponseH\x00\x42\n\n\x08response\"$\n\x0b\x43ustomError\x12\x15\n\rerror_message\x18\x01 \x01(\t\"T\n\x0b\x45\x63hoRequest\x12\x0c\n\x04text\x18\x01 \x01(\t\x12\x37\n\x0cvoice_config\x18\x02 \x01(\x0b\x32!.virtualfriends_proto.VoiceConfig\"R\n\x0c\x45\x63hoResponse\x12\x0c\n\x04text\x18\x01 \x01(\t\x12\x0e\n\x06\x61\x63tion\x18\x02 \x01(\t\x12\x11\n\tsentiment\x18\x03 \x01(\t\x12\x11\n\treply_wav\x18\x04 \x01(\x0c\"S\n\x0bVoiceConfig\x12\x33\n\nvoice_type\x18\x01 \x01(\x0e\x32\x1f.virtualfriends_proto.VoiceType\x12\x0f\n\x07octaves\x18\x02 \x01(\x02\"=\n\x0fMirroredContent\x12\x16\n\x0e\x63haracter_name\x18\x01 \x01(\t\x12\x12\n\nsession_id\x18\x02 \x01(\x03\"\xf6\x01\n\x19StreamReplyMessageRequest\x12?\n\x10mirrored_content\x18\x01 \x01(\x0b\x32%.virtualfriends_proto.MirroredContent\x12\x15\n\rjson_messages\x18\x02 \x03(\t\x12\x16\n\x0e\x63ustom_prompts\x18\x07 \x01(\t\x12\r\n\x03wav\x18\x03 \x01(\x0cH\x00\x12\x0e\n\x04text\x18\x06 \x01(\tH\x00\x12\x37\n\x0cvoice_config\x18\x05 \x01(\x0b\x32!.virtualfriends_proto.VoiceConfigB\x11\n\x0f\x63urrent_message\"\xea\x01\n\x1aStreamReplyMessageResponse\x12?\n\x10mirrored_content\x18\x06 \x01(\x0b\x32%.virtualfriends_proto.MirroredContent\x12\x15\n\rreply_message\x18\x01 \x01(\t\x12\x0e\n\x06\x61\x63tion\x18\x02 \x01(\t\x12\x11\n\tsentiment\x18\x03 \x01(\t\x12\x11\n\treply_wav\x18\x04 \x01(\x0c\x12\x18\n\x10transcribed_text\x18\x05 \x01(\t\x12\x13\n\x0b\x63hunk_index\x18\x07 \x01(\x05\x12\x0f\n\x07is_stop\x18\x08 \x01(\x08\"j\n\x1a\x44ownloadAssetBundleRequest\x12\x16\n\x0epublisher_name\x18\x01 \x01(\t\x12\x16\n\x0e\x63haracter_name\x18\x02 \x01(\t\x12\x18\n\x10runtime_platform\x18\x03 \x01(\t:\x02\x18\x01\"T\n\x1b\x44ownloadAssetBundleResponse\x12\r\n\x05\x63hunk\x18\x01 \x01(\x0c\x12\r\n\x05index\x18\x02 \x01(\x05\x12\x13\n\x0btotal_count\x18\x03 \x01(\x05:\x02\x18\x01\"S\n\x10MirroredBlobInfo\x12\x11\n\tblob_name\x18\x01 \x01(\t\x12\x15\n\rmajor_version\x18\x02 \x01(\x05\x12\x15\n\rminor_version\x18\x03 \x01(\x05\"Y\n\x13\x44ownloadBlobRequest\x12\x42\n\x12mirrored_blob_info\x18\x01 \x01(\x0b\x32&.virtualfriends_proto.MirroredBlobInfo\"\x8d\x01\n\x14\x44ownloadBlobResponse\x12\x42\n\x12mirrored_blob_info\x18\x01 \x01(\x0b\x32&.virtualfriends_proto.MirroredBlobInfo\x12\r\n\x05\x63hunk\x18\x02 \x01(\x0c\x12\r\n\x05index\x18\x03 \x01(\x05\x12\x13\n\x0btotal_count\x18\x04 \x01(\x05\")\n\x13LoaderReadyPlayerMe\x12\x12\n\navatar_url\x18\x01 \x01(\t\"+\n\x13GetCharacterRequest\x12\x14\n\x0c\x63haracter_id\x18\x01 \x01(\t\"\xee\x01\n\x14GetCharacterResponse\x12I\n\x14loader_readyplayerme\x18\x01 \x01(\x0b\x32).virtualfriends_proto.LoaderReadyPlayerMeH\x00\x12,\n\x06gender\x18\x02 \x01(\x0e\x32\x1c.virtualfriends_proto.Gender\x12\x13\n\x0b\x66riend_name\x18\x03 \x01(\t\x12\x37\n\x0cvoice_config\x18\x04 \x01(\x0b\x32!.virtualfriends_proto.VoiceConfigB\x0f\n\rloader_config*\x89\x01\n\tVoiceType\x12\x15\n\x11VoiceType_Invalid\x10\x00\x12\x18\n\x14VoiceType_NormalMale\x10\x01\x12\x1b\n\x17VoiceType_NormalFemale1\x10\x02\x12\x1b\n\x17VoiceType_NormalFemale2\x10\x03\x12\x11\n\rVoiceType_Orc\x10\x04*@\n\x06Gender\x12\x12\n\x0eGender_Invalid\x10\x00\x12\x0f\n\x0bGender_Male\x10\x01\x12\x11\n\rGender_Female\x10\x02\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'ws_message_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _DOWNLOADASSETBUNDLEREQUEST._options = None
  _DOWNLOADASSETBUNDLEREQUEST._serialized_options = b'\030\001'
  _DOWNLOADASSETBUNDLERESPONSE._options = None
  _DOWNLOADASSETBUNDLERESPONSE._serialized_options = b'\030\001'
  _globals['_VOICETYPE']._serialized_start=2615
  _globals['_VOICETYPE']._serialized_end=2752
  _globals['_GENDER']._serialized_start=2754
  _globals['_GENDER']._serialized_end=2818
  _globals['_VFREQUEST']._serialized_start=43
  _globals['_VFREQUEST']._serialized_end=494
  _globals['_VFRESPONSE']._serialized_start=497
  _globals['_VFRESPONSE']._serialized_end=927
  _globals['_CUSTOMERROR']._serialized_start=929
  _globals['_CUSTOMERROR']._serialized_end=965
  _globals['_ECHOREQUEST']._serialized_start=967
  _globals['_ECHOREQUEST']._serialized_end=1051
  _globals['_ECHORESPONSE']._serialized_start=1053
  _globals['_ECHORESPONSE']._serialized_end=1135
  _globals['_VOICECONFIG']._serialized_start=1137
  _globals['_VOICECONFIG']._serialized_end=1220
  _globals['_MIRROREDCONTENT']._serialized_start=1222
  _globals['_MIRROREDCONTENT']._serialized_end=1283
  _globals['_STREAMREPLYMESSAGEREQUEST']._serialized_start=1286
  _globals['_STREAMREPLYMESSAGEREQUEST']._serialized_end=1532
  _globals['_STREAMREPLYMESSAGERESPONSE']._serialized_start=1535
  _globals['_STREAMREPLYMESSAGERESPONSE']._serialized_end=1769
  _globals['_DOWNLOADASSETBUNDLEREQUEST']._serialized_start=1771
  _globals['_DOWNLOADASSETBUNDLEREQUEST']._serialized_end=1877
  _globals['_DOWNLOADASSETBUNDLERESPONSE']._serialized_start=1879
  _globals['_DOWNLOADASSETBUNDLERESPONSE']._serialized_end=1963
  _globals['_MIRROREDBLOBINFO']._serialized_start=1965
  _globals['_MIRROREDBLOBINFO']._serialized_end=2048
  _globals['_DOWNLOADBLOBREQUEST']._serialized_start=2050
  _globals['_DOWNLOADBLOBREQUEST']._serialized_end=2139
  _globals['_DOWNLOADBLOBRESPONSE']._serialized_start=2142
  _globals['_DOWNLOADBLOBRESPONSE']._serialized_end=2283
  _globals['_LOADERREADYPLAYERME']._serialized_start=2285
  _globals['_LOADERREADYPLAYERME']._serialized_end=2326
  _globals['_GETCHARACTERREQUEST']._serialized_start=2328
  _globals['_GETCHARACTERREQUEST']._serialized_end=2371
  _globals['_GETCHARACTERRESPONSE']._serialized_start=2374
  _globals['_GETCHARACTERRESPONSE']._serialized_end=2612
# @@protoc_insertion_point(module_scope)
