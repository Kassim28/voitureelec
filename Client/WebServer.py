from flask import Flask, request, render_template
import requests
from zeep import Client
import json
import folium
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport 

# Flask constructor
app = Flask(__name__)
@app.route("/", methods=['GET', 'POST'])
def start():
   return render_template('index.html')



@app.route("/calculatrice", methods=['GET', 'POST'])
def Calculatrice(autonomie,distance):
    url = 'http://192.168.1.68:8000/?wsdl'
    client = Client(url)
    autonomie = 200
    distance = 400
    distance_gps = autonomie * 1000
    if request.method == "POST":
       autonomie = request.form.get("autonomie")
       distance = request.form.get("distance")
    res = client.service.ETA(autonomie, distance)
    return render_template('index.html',distance=distance, autonomie=autonomie,res=res)

@app.route("/bornes", methods=['GET', 'POST'])
#fonction qui retourne un tableau avec les coordonnees GPS d'une borne dans un rayon de 10 KM 
#cette fonction prend comme variable les coordonnes de la forme suivante: [latitude,longitude]
def geofilter(coordonnees):
   latitude = coordonnees[0]
   longitude = coordonnees[1]
   rayon = 10000 #rayon de recherche des bornes
   nb_bornes = 1
   
   url = 'https://odre.opendatasoft.com/api/records/1.0/search/?dataset=bornes-irve&q=&rows=' + str(nb_bornes) + '&facet=region&facet=departement&geofilter.distance=' + str(latitude) + '%2C' + str(longitude) + '%2C' + str(rayon)
   res = requests.get(url) 
   res = res.json()
   tab = []
   #for i in range(nb_bornes - 1):
   tab.append(tuple(res["records"][0]["fields"]["geo_point_borne"])) # ajoute au tableau la liste des bornes
   return tab
   
@app.route("/geo", methods=['GET', 'POST'])
def carte():
   tooltip = ""

   latitude_depart = 55.720041
   longitude_depart = 37.610376
   
   latitude_arrivee = 43.274699
   longitude_arrivee = 5.384757
   
   depart = [latitude_depart,longitude_depart]
   arrivee = [latitude_arrivee,longitude_arrivee]

   headers = {'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',}
   api_key = '5b3ce3597851110001cf62485f5fee809b214c329e05166228f3f13d' #openroute token 
   res = requests.get('https://api.openrouteservice.org/v2/directions/driving-car?api_key=' + api_key + '&start=' + str(longitude_depart) + ',' + str(latitude_depart) + '&end=' + str(longitude_arrivee) + ',' + str(latitude_arrivee) , headers=headers)
   res = res.json()

   distance = res["features"][0]["properties"]["summary"]["distance"] #distance du trajet en metres

   autonomie = 15 #Autonomie de la voiture en km
   autonomie_10 = round(autonomie/10)
   distance_parcourue = 0

   trajet = [] #tableau qui prend la liste des coordonnes GPS pour le trajet
   
   i = res["features"][0]["properties"]["way_points"][1] # nombre total de coordonnees GPS pour le trajet

   for i in range(i-1): # boucle qui rajoute les coordonnes GPS dans un tableau pour le trajet
      longitude = res["features"][0]["geometry"]["coordinates"][i][0]
      latitude = res["features"][0]["geometry"]["coordinates"][i][1]
      trajet.append(tuple([latitude,longitude])) # ajoute au tableau la liste des coordonées GPS


   m = folium.Map(location=[46.3622, 1.5231], zoom_start=6) #Affiche la carte avec les coordonnes GPS du centre de la France

   
   folium.Marker(depart, popup="<i>Depart</i>", icon=folium.Icon(icon="flag", color="blue"), tooltip=tooltip).add_to(m) #drapeau depart en bleu
   folium.Marker(arrivee, popup="<b>Arrivee</b>", icon=folium.Icon(icon="flag", color="red"), tooltip=tooltip).add_to(m) #drapeau arrivee en rouge
   """
   for i in range(i-1): # boucle qui rajoutes markers pour les bornes!
      longitude = res["features"][0]["geometry"]["coordinates"][i][0]
      latitude = res["features"][0]["geometry"]["coordinates"][i][1]
      coordonnee_trajet = [latitude,longitude]
      coordonnees_borne = geofilter(coordonnee_trajet)
   """
      #folium.Marker(list(coordonnees_borne[0]), tooltip=tooltip).add_to(m)

   folium.PolyLine(trajet,color='red',weight=15,opacity=0.8).add_to(m)

   return m._repr_html_()

@app.route("/graphql", methods=['GET', 'POST'])
#https://developers.chargetrip.com/api-reference/cars/query-cars#query
def query(): 
   headers = {'Content-Type':'application/json','x-client-id':'633d9583be646cad8986e55e','x-app-id':'633d9583be646cad8986e560'}

   # Select your transport with a defined url endpoint
   transport = AIOHTTPTransport(url="https://api.chargetrip.io/graphql", headers=headers)

   # Create a GraphQL client using the defined transport
   client = Client(transport=transport, fetch_schema_from_transport=True)

   # Provide a GraphQL query
   size = 20 #nombre de voitures à afficher
   query = gql(
      """
      query carListAll {
         carList (size:""" + str(size) + """){ 
            id
            naming {
               make
               model
               version
               edition
               chargetrip_version
            }
             battery {
               usable_kwh
               full_kwh
            }
            connectors {
               standard
               power
               time
               speed
            }
            adapters {
               standard
               power
               time
               speed
            }
            range {
               chargetrip_range {
               best
               worst
               }
            }
         }
         }
      """
 )

   # Execute the query on the transport
   res = client.execute(query)
   list_Voiture = [] #Liste de voitures avec le nom, l'autonomie en km et le temps de rechargement en minutes.
   for i in range(size-1):

      voiture = []

      nom_voiture = res["carList"][i]["naming"]["make"] + " " + res["carList"][i]["naming"]["model"] #nom de la voiture avec le modèle
      voiture.append(nom_voiture)

      autonomie_voiture = res["carList"][i]["range"]["chargetrip_range"]["best"] #autonomie en km
      voiture.append(autonomie_voiture)

      temps_rechargement_voiture = res["carList"][i]["connectors"][1]["time"] #duree de rechargement de 10 à 80% en minutes
      voiture.append(temps_rechargement_voiture)

      list_Voiture.append(voiture)

   print(list_Voiture)
   return res