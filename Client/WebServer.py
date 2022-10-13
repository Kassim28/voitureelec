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
   listeVoitures = query()

   if request.method == "GET":
      return render_template('index.html',listeVoitures=listeVoitures)

   if request.method == "POST":
      autonomie_voiture = request.form.get("autonomie") #recupere l'autonomie de la voiture solicitée
      depart = request.form.get("depart") #recupere le nom de la ville de départ
      arrivee = request.form.get("arrivee") #recupere le nom de la ville d'arrivée
      calculatrice_duree(autonomie_voiture,distance(depart,arrivee))
      coordonnees_depart = geocode(depart)
      coordonnees_arrivee = geocode(arrivee)
      return carte(coordonnees_depart,coordonnees_arrivee,autonomie_voiture)

@app.route("/calculatrice", methods=['GET', 'POST'])
def calculatrice_duree(autonomie,distance):
    url = 'http://192.168.56.103:8000/?wsdl'
    client = Client(url)
    res = client.service.ETA(autonomie, distance)
    return res

@app.route("/bornes", methods=['GET', 'POST'])
#fonction qui retourne un tableau avec les coordonnees GPS d'une borne dans un rayon de 10 KM 
#cette fonction prend comme variable les coordonnes de la forme suivante: [latitude,longitude]
def geofilter_bornes(coordonnees):
   latitude = coordonnees[0]
   longitude = coordonnees[1]
   rayon = 100000 #rayon de recherche des bornes
   nb_bornes = 1
   
   url = 'https://odre.opendatasoft.com/api/records/1.0/search/?dataset=bornes-irve&q=&rows=' + str(nb_bornes) + '&facet=region&facet=departement&geofilter.distance=' + str(latitude) + '%2C' + str(longitude) + '%2C' + str(rayon)
   res = requests.get(url) 
   res = res.json()
   coordonnes_bornes = ()
   coordonnes_bornes = tuple(res["records"][0]["fields"]["geo_point_borne"]) # ajoute dans un tuple les coordonnees d'une borne
   return coordonnes_bornes
   
@app.route("/geo", methods=['GET', 'POST'])
def distance(depart,arrivee):
   latitude_depart = depart[0]
   longitude_depart = depart[1]
   latitude_arrivee = arrivee[0]
   longitude_arrivee = arrivee[1]
   headers = {'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',}
   api_key = '5b3ce3597851110001cf62485f5fee809b214c329e05166228f3f13d' #openroute token 
   res = requests.get('https://api.openrouteservice.org/v2/directions/driving-car?api_key=' + api_key + '&start=' + str(longitude_depart) + ',' + str(latitude_depart) + '&end=' + str(longitude_arrivee) + ',' + str(latitude_arrivee) , headers=headers)
   res = res.json()
   distance = res["features"][0]["properties"]["summary"]["distance"]  #distance du trajet en km
   return distance / 1000

def carte(depart,arrivee,autonomie):
   tooltip = ""

   latitude_depart = depart[0]
   longitude_depart = depart[1]
   
   latitude_arrivee = arrivee[0]
   longitude_arrivee = arrivee[1]
   headers = {'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',}
   api_key = '5b3ce3597851110001cf62485f5fee809b214c329e05166228f3f13d' #openroute token 
   res = requests.get('https://api.openrouteservice.org/v2/directions/driving-car?api_key=' + api_key + '&start=' + str(longitude_depart) + ',' + str(latitude_depart) + '&end=' + str(longitude_arrivee) + ',' + str(latitude_arrivee) , headers=headers)
   res = res.json()
   distance = res["features"][0]["properties"]["summary"]["distance"] #distance du trajet en metres
  
   trajet = [] #tableau qui prend la liste des coordonnes GPS pour le trajet
   
   i = res["features"][0]["properties"]["way_points"][1] # nombre total de coordonnees GPS pour le trajet
   
   print(i)
   autonomie = int(autonomie) * 1000
   autonomie_10 = round(autonomie/10)

   etape = 0
   waypoint_num = 0  
   distance_parcourue = 0
      
   for i in range(i-1): # boucle qui rajoute les coordonnes GPS dans un tableau pour le trajet
      etapes_waypoints = res["features"][0]["properties"]["segments"][0]["steps"][etape]["way_points"][1]
      print("num etap waypoints est" + str(etapes_waypoints))
      if (etapes_waypoints == i):
         break
      else:
         longitude = res["features"][0]["geometry"]["coordinates"][i][0]
         latitude = res["features"][0]["geometry"]["coordinates"][i][1]
         waypoint_num += 1
         print("num waypoint est : " + str(waypoint_num))
         if (waypoint_num == etapes_waypoints):
            distance_parcourue += round(res["features"][0]["properties"]["segments"][0]["steps"][etape]["distance"])
            etape += 1
            print("etape =" + str(etape))
            print("distance parcourue est de " + str(distance_parcourue) + " mètres")
            if ((autonomie - distance_parcourue) >= autonomie_10):
               trajet.append(tuple([latitude,longitude])) # ajoute au tableau la liste des coordonées GPS      
            else:
               coordonnes_bornes = [latitude,longitude]
               trajet.append(geofilter_bornes(coordonnes_bornes))
               print("RECHARGEMENT!!!!!!!!!")
               distance_parcourue = 0
         else:
            trajet.append(tuple([latitude,longitude])) # ajoute au tableau la liste des coordonées GPS      
   print("la distance est de " + str(distance) + "km")
   print
   m = folium.Map(location=[46.3622, 1.5231], zoom_start=6) #Affiche la carte avec les coordonnes GPS du centre de la France

   
   folium.Marker(depart, popup="<i>Depart</i>", icon=folium.Icon(icon="flag", color="blue"), tooltip=tooltip).add_to(m) #drapeau depart en bleu
   folium.Marker(arrivee, popup="<b>Arrivee</b>", icon=folium.Icon(icon="flag", color="red"), tooltip=tooltip).add_to(m) #drapeau arrivee en rouge

   folium.PolyLine(trajet,color='red',weight=15,opacity=0.8).add_to(m)

   return m._repr_html_()

@app.route("/geocode", methods=['GET', 'POST'])
def geocode(ville):
   headers = {'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',}
   api_key = '5b3ce3597851110001cf62485f5fee809b214c329e05166228f3f13d' #openroute token 
   res_ville = requests.get('https://api.openrouteservice.org/geocode/search?api_key=' + api_key + '&text=' + str(ville), headers=headers)
   res_ville = res_ville.json()
   longitude = res_ville["features"][0]["geometry"]["coordinates"][0]
   latitude = res_ville["features"][0]["geometry"]["coordinates"][1]
   coordonnees_ville = [latitude,longitude]
   return coordonnees_ville

@app.route("/graphql", methods=['GET', 'POST'])
#https://developers.chargetrip.com/api-reference/cars/query-cars#query
def query(): 
   if request.method == "GET":
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

      return list_Voiture

         