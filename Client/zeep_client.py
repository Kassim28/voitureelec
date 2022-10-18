from zeep import Client

def calculatrice_duree(autonomie,distance,rechargement):
    url = 'http://192.168.56.103:8000/?wsdl'
    client = Client(url)
    res = client.service.ETA(autonomie, distance, rechargement)
    return res