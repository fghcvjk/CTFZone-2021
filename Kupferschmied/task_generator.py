from Crypto.Util.number import getPrime, bytes_to_long
FLAG = b"#################################################"

def enc(m):
    return pow(m, e, N)

if __name__ == "__main__":    
    l = 256
    p = getPrime(1024)
    N = p * getPrime(1024)
    e = 65537
    a = (p >> l) << l
    print("N:", N)
    print("Known part of p:", hex(a))
    print("Length of the unknown part:", l)
    print("enc:", enc(bytes_to_long(FLAG)))
