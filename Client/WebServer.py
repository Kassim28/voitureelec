from flask import Flask, request, render_template
import requests
from zeep_client import *
import json
import folium
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport 

# Flask constructor
app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def start():
   listeVoitures = query()
   autonomie_voiture = 0
   distance_trajet = 0
   duree_trajet = 0
   if request.method == "GET":
      return render_template('index.html',listeVoitures=listeVoitures,autonomie_voiture=autonomie_voiture,distance_trajet=distance_trajet,duree_trajet=duree_trajet)
   
   if request.method == "POST":
      voiture_choisie = request.form.get("voiture_choisie") #recupere l'autonomie de la voiture solicitée
      depart = request.form.get("depart") #recupere le nom de la ville de départ
      arrivee = request.form.get("arrivee") #recupere le nom de la ville d'arrivée
      autonomie_voiture = list(voiture_choisie.split())[-2].replace(',', '')
      rechargement_voiture = list(voiture_choisie.split())[-1].replace(']', '')
      distance_trajet = distance(depart,arrivee)
      duree_trajet = calculatrice_duree(autonomie_voiture,distance_trajet,rechargement_voiture)
      print("L'autonomie de la voiture est de " + autonomie_voiture + " km.")
      print("Le temps de rechargement de la voiture est de " + rechargement_voiture + " minutes.")
      print("La distance du trajet est de " + str(distance(depart,arrivee)) + " mètres.")
      print("La durée du trajet est de " + str(calculatrice_duree(autonomie_voiture,distance(depart,arrivee),rechargement_voiture)) + " h.")
      return render_template('map.html',listeVoitures=listeVoitures,autonomie_voiture=autonomie_voiture,distance_trajet=distance_trajet,duree_trajet=duree_trajet,depart=depart,arrivee=arrivee)  

@app.route("/carte", methods=['GET', 'POST'])
def afficher_carte():
   listeVoitures = query()

   if request.method == "GET":
      return render_template('map.html',listeVoitures=listeVoitures,autonomie_voiture=autonomie_voiture,distance_trajet=distance_trajet,duree_trajet=duree_trajet)

   if request.method == "POST":
      
      autonomie_voiture = request.form.get("autonomie_voiture")
      depart = request.form.get("depart")
      arrivee = request.form.get("arrivee")
      coordonnees_depart = geocode(depart)
      coordonnees_arrivee = geocode(arrivee)
      return carte(coordonnees_depart,coordonnees_arrivee,autonomie_voiture)


#fonction qui retourne un tableau avec les coordonnees GPS d'une borne dans un rayon de 10 KM 
#cette fonction prend comme variable les coordonnes de la forme suivante: [latitude,longitude]
def geofilter_bornes(coordonnees):
   latitude = coordonnees[0]
   longitude = coordonnees[1]
   rayon = 100000 #rayon de recherche des bornes en mètres
   nb_bornes = 1
   
   url = 'https://odre.opendatasoft.com/api/records/1.0/search/?dataset=bornes-irve&q=&rows=' + str(nb_bornes) + '&facet=region&facet=departement&geofilter.distance=' + str(latitude) + '%2C' + str(longitude) + '%2C' + str(rayon)
   res = requests.get(url) 
   res = res.json()
   coordonnes_bornes = ()
   coordonnes_bornes = tuple(res["records"][0]["fields"]["geo_point_borne"]) # ajoute dans un tuple les coordonnees d'une borne
   return coordonnes_bornes
   

def distance(depart,arrivee):
   depart_trajet = geocode(depart)
   arrivee_trajet = geocode(arrivee)

   latitude_depart = depart_trajet[0]
   longitude_depart = depart_trajet[1]
   latitude_arrivee = arrivee_trajet[0]
   longitude_arrivee = arrivee_trajet[1]
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

   m = folium.Map(location=[46.3622, 1.5231], zoom_start=6) #Affiche la carte avec les coordonnes GPS du centre de la France
      
   for i in range(i-1): # boucle qui rajoute les coordonnes GPS dans un tableau pour le trajet
      etapes_waypoints = res["features"][0]["properties"]["segments"][0]["steps"][etape]["way_points"][1]
      #print("num etap waypoints est" + str(etapes_waypoints))
      if (etapes_waypoints == i):
         break
      else:
         longitude = res["features"][0]["geometry"]["coordinates"][i][0]
         latitude = res["features"][0]["geometry"]["coordinates"][i][1]
         waypoint_num += 1
         #print("num waypoint est : " + str(waypoint_num))
         if (waypoint_num == etapes_waypoints):
            distance_parcourue += round(res["features"][0]["properties"]["segments"][0]["steps"][etape]["distance"])
            etape += 1
            print("etape =" + str(etape))
            print("distance parcourue est de " + str(distance_parcourue) + " mètres")
            if ((autonomie - distance_parcourue) >= autonomie_10):
               trajet.append(tuple([latitude,longitude])) # ajoute au tableau la liste des coordonées GPS      
            else:
               coordonnes = [latitude,longitude]
               coordonnes_bornes = geofilter_bornes(coordonnes)
               folium.Marker(coordonnes_bornes, popup="<i>Borne</i>", icon=folium.Icon(color="green"), tooltip=tooltip).add_to(m) #drapeaude borne en bleu
               print("RECHARGEMENT!!!!!!!!!")
               distance_parcourue = 0
         else:
            trajet.append(tuple([latitude,longitude])) # ajoute au tableau la liste des coordonées GPS      
   print("la distance est de " + str(round(distance)) + " m")
   
   folium.Marker(depart, popup="<i>Depart</i>", icon=folium.Icon(icon="flag", color="blue"), tooltip=tooltip).add_to(m) #drapeau depart en bleu
   folium.Marker(arrivee, popup="<b>Arrivee</b>", icon=folium.Icon(icon="flag", color="red"), tooltip=tooltip).add_to(m) #drapeau arrivee en rouge

   folium.PolyLine(trajet,color='red',weight=15,opacity=0.8).add_to(m)

   return m._repr_html_()


def geocode(ville):
   headers = {'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',}
   api_key = '5b3ce3597851110001cf62485f5fee809b214c329e05166228f3f13d' #openroute token 
   res_ville = requests.get('https://api.openrouteservice.org/geocode/search?api_key=' + api_key + '&text=' + str(ville), headers=headers)
   res_ville = res_ville.json()
   longitude = res_ville["features"][0]["geometry"]["coordinates"][0]
   latitude = res_ville["features"][0]["geometry"]["coordinates"][1]
   coordonnees_ville = [latitude,longitude]
   return coordonnees_ville


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
   return list_Voiture

      