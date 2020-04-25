from cs50 import SQL
db = SQL("sqlite:///finance.db")

data = db.execute("SELECT (symbol), SUM(nshares) FROM transactions WHERE user_id = ? GROUP BY symbol", 9)
lista = []
i = 0
for row in data:
    if data[i]['SUM(nshares)'] == 0:
        lista.append(i)
    i += 1
lista.sort(reverse = True)

for b in lista:
    del data[b]
print(data)
print(lista)