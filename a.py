import http.client

conn = http.client.HTTPSConnection("exercisedb.p.rapidapi.com")

headers = {
    'x-rapidapi-key': "040145ce03msh97371a561660ef0p1ebc6ejsn858afa1b288d",
    'x-rapidapi-host': "exercisedb.p.rapidapi.com"
}

conn.request("GET", "/exercises/name/%7Bname%7D?offset=0&limit=10", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))