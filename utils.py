import hashlib
import base64

from Crypto.Cipher import AES


class AESCipher:

    def __init__(self, key):
        self.bs = AES.block_size
        self.key = hashlib.sha256(AESCipher.str_to_bytes(key)).digest()
    
    @staticmethod
    def str_to_bytes(data):
        u_type = type(b''.decode('utf8'))
        if isinstance(data, u_type):
            return data.encode('utf8')
        return data
    
    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]
    
    def decrypt(self, enc):
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return  self._unpad(cipher.decrypt(enc[AES.block_size:]))
    
    def decrypt_string(self, enc):
        enc = base64.b64decode(enc)
        return  self.decrypt(enc).decode('utf8')


def decrypt_aes(key, encrypt):
    cipher = AESCipher(key)
    return cipher.decrypt_string(encrypt)


if __name__ == '__main__':
    encrypt = 'P37w+VZImNgPEO1RBhJ6RtKl7n6zymIbEG1pReEzghk='
    key = 'test key'
    print(decrypt_aes(key, encrypt))