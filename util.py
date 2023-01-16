from secrets import randbits

def random_128_bit_string():
  num = randbits(128)
  arr = []
  arr_append = arr.append
  _divmod = divmod
  ALPHABET = "23456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
  base = len(ALPHABET)
  while num:
    num, rem = _divmod(num, base)
    arr_append(ALPHABET[rem])
  return ''.join(arr)
