from spyne import Application, rpc, ServiceBase, Unicode, Iterable, Integer, String, Float
from spyne.server.wsgi import WsgiApplication
from spyne.protocol.soap import Soap11
from wsgiref.simple_server import make_server

class  ServiceCalculatrice(ServiceBase):

    @rpc(Integer, Integer, _returns=Float)
    #fonction qui permet de calculer la durée estimée d'arrivée
    def ETA(ctx, autonomie, distance):
        rechargement_borne = 1.5 #en heures
        vitesse = 90 #en km/h
        durée = distance / vitesse #durée en Km/h
        nb_bornes = distance / autonomie #nombre de bornes traversés

        if (distance <= autonomie):
            return round(durée,2) #arrondi la durée estimée (float) à deux chiffres après la virgule
        else:
            durée_estimée = durée + (rechargement_borne * nb_bornes) #la durée estimée prend en compte le temps de rechargement
            return round(durée_estimée,2)
       
application = Application([ServiceCalculatrice], 'spyne.examples.hello.soap',
 in_protocol=Soap11(validator='lxml'),
 out_protocol=Soap11())

wsgi_application = WsgiApplication(application)

server = make_server('192.168.1.68', 8000, wsgi_application)
server.serve_forever()