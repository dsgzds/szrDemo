#! /usr/bin/env python

# Copyright (c) 2013, martysama0134
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
# Neither the name of martysama0134 nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""XTEA Block Cipher Module

Algorithm: http://www.cix.co.uk/~klockstone/xtea.pdf
See also: http://en.wikipedia.org/wiki/XTEA

Usage:

	Basically:
	>>> from xtea import xtea_encrypt, xtea_decrypt
	>>> xtea_testkey = '5EE75350215099170BA771E0CEA40134'.decode('hex')
	>>> a = xtea_encrypt('abcdefgh', xtea_testkey)
	>>> xtea_decrypt(a, xtea_testkey)
	'abcdefgh'
	
	Entire string process:
	>>> from xtea import xtea_encrypt_all, xtea_decrypt_all
	>>> xtea_testkey = '5EE75350215099170BA771E0CEA40134'.decode('hex')
	>>> b = xtea_encrypt_all('*** this is a string ***', xtea_testkey)
	>>> xtea_decrypt_all(b, xtea_testkey)
	'*** this is a string ***'
	
	Class implementation:
	>>> from xtea import XTEA
	>>> xtea_testkey = '5EE75350215099170BA771E0CEA40134'.decode('hex')
	>>> myxtea = XTEA(xtea_testkey)
	>>> myxtea.decrypt(myxtea.encrypt('abcdefgh'))
	'abcdefgh'
	
	>>> from xtea import XTEA
	>>> xtea_testkey = '5EE75350215099170BA771E0CEA40134'.decode('hex')
	>>> myxtea = XTEA(xtea_testkey)
	>>> myxtea.decrypt_all(myxtea.encrypt_all('*** this is a string ***'))
	'*** this is a string ***'
"""
__author__		= "martysama0134"
__copyright__	= "Copyright (c) 2013 martysama0134"
__date__		= "2013-07-12"
__license__		= "New BSD License"
__url__			= "https://code.google.com/p/python-tea/"
__version__		= "1.8.20130712"

import struct

XTEA_DELTA = 0x9E3779B9
XTEA_N = 32

def xtea_encrypt(block, key, endian="!"):
	"""Encrypt 32 bit data block using XTEA block cypher
		* block = 64 bit/8 bytes (byte string)
		* key = 128 bit/16 bytes (byte string)
		* endian = byte order (default '!', commonly used '<' and '>'; see also 'struct' module documentation) (string)
	"""
	(pack, unpack) = (struct.pack, struct.unpack)
	
	(y, z) = unpack(endian+"2L", block)
	k = unpack(endian+"4L", key)
	
	global XTEA_DELTA, XTEA_N
	(sum, delta, n) = 0, XTEA_DELTA, XTEA_N
	
	for i in range(n):
		y = (y + (((z<<4 ^ z>>5) + z) ^ (sum + k[sum&3]))) & 0xFFFFFFFF
		sum = (sum + delta) & 0xFFFFFFFF
		z = (z + (((y<<4 ^ y>>5) + y) ^ (sum + k[sum>>11 &3]))) & 0xFFFFFFFF
	return pack(endian+"2L", y, z)

def xtea_decrypt(block, key, endian="!"):
	"""Decrypt 32 bit data block using XTEA block cypher
		* block = 64 bit/8 bytes (byte string)
		* key = 128 bit/16 bytes (byte string)
		* endian = byte order (default '!', commonly used '<' and '>'; see also 'struct' module documentation) (string)
	"""
	(pack, unpack) = (struct.pack, struct.unpack)
	
	(y, z) = unpack(endian+"2L", block)
	k = unpack(endian+"4L", key)
	
	global XTEA_DELTA, XTEA_N
	(sum, delta, n) = 0, XTEA_DELTA, XTEA_N
	
	sum = (delta * n) & 0xFFFFFFFF
	for i in range(n):
		z = (z - (((y<<4 ^ y>>5) + y) ^ (sum + k[sum>>11 &3]))) & 0xFFFFFFFF
		sum = (sum - delta) & 0xFFFFFFFF
		y = (y - (((z<<4 ^ z>>5) + z) ^ (sum + k[sum&3]))) & 0xFFFFFFFF
	return pack(endian+"2L", y, z)

def xtea_encrypt_all(data, key, endian="!"):
	"""Encrypt a entire string using XTEA block cypher"""
	newdata = ''
	data_s = len(data)
	data_p = data_s%8
	if data_p:
		data_pl = 8-data_p
		data+=(data_pl*chr(0))
		data_s+=data_pl
	for i in range(data_s/8):
		block = data[i*8:(i*8)+8]
		newdata+=xtea_encrypt(block, key, endian)
	return newdata

def xtea_decrypt_all(data, key, endian="!"):
	"""Decrypt a entire string using XTEA block cypher"""
	newdata = ''
	data_s = len(data)
	data_p = data_s%8
	if data_p:
		data_pl = 8-data_p
		data+=(data_pl*chr(0))
		data_s+=data_pl
	for i in range(data_s/8):
		block = data[i*8:(i*8)+8]
		newdata+=xtea_decrypt(block, key, endian)
	return newdata

class XTEA(object):
	"""XTEA class implementation"""
	def __init__(self, key, endian="!"):
		self.key = key
		self.endian = endian

	def encrypt(self, block):
		global xtea_encrypt
		return xtea_encrypt(block, self.key, self.endian)

	def decrypt(self, block):
		global xtea_decrypt
		return xtea_decrypt(block, self.key, self.endian)

	def encrypt_all(self, data):
		global xtea_encrypt_all
		return xtea_encrypt_all(data, self.key, self.endian)

	def decrypt_all(self, data):
		global xtea_decrypt_all
		return xtea_decrypt_all(data, self.key, self.endian)

if __name__ == '__main__':
    import base64
    key = bytes.fromhex('5EE75350215099170BA771E0CEA40134')
    uid = 5131730524704768
    uid = 917273531090210816
    for i in range(10):
        uid += i
        print(uid)
        uid_byte = uid.to_bytes(length=8, byteorder='big', signed=False)
        a = xtea_encrypt(uid_byte, key)
        print(a, a.hex(), base64.b64encode(a), base64.urlsafe_b64encode(a))
        b = xtea_decrypt(a, key)
        print(b, int.from_bytes(b, byteorder='big', signed=False))
