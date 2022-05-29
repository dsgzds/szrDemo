import id_gen

gen = id_gen.generator(1, 1)
for _ in range(10):
    uid = next(gen)
    text = id_gen.uid2text(uid)
    duid = id_gen.text2uid(text)
    print(uid, text, duid)
