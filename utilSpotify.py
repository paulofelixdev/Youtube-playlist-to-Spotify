from spotipy import (
    Spotify,
    CLIENT_CREDS_ENV_VARS as CCEV,
    prompt_for_user_token,
    SpotifyException,
)
import sys, os, warnings
import json
from fuzzywuzzy import fuzz #Comparar strings em percentagem
from utilYoutube import UtilYoutube
from spotipy.oauth2 import SpotifyClientCredentials


class UtilSpotify():

    def __init__(self, playlistName, playlistId, public, description):
        self.playlistName = playlistName
        self.playlistId = playlistId
        self.public = public
        self.description = description
        self.Spotify = self.login()
        self.user = self.Spotify.current_user()

    #Obter palavras chave para filtrar nomes do youtube
    def getKeywords(self):
        #Carregar keywords
        with open("keywords.json") as file:
            keywords = json.load(file)
            return keywords

    #Fazer login
    def login(self):
        scopes = ('playlist-read-collaborative '
                  'playlist-modify-public '
                  'playlist-read-private '
                  'playlist-modify-private ')

        with open("config.json") as file:
            jsonFile = json.load(file)
            username = jsonFile["Spotify"]["username"]
            CLIENT_ID = jsonFile["Spotify"]["CLIENT_ID"]
            CLIENT_SECRET = jsonFile["Spotify"]["CLIENT_SECRET"]
            REDIRECT_URI = jsonFile["Spotify"]["REDIRECT_URI"]


        token = prompt_for_user_token(username=username, client_id=CLIENT_ID,
                                      client_secret=CLIENT_SECRET,
                                      redirect_uri=REDIRECT_URI, scope=scopes)

        return Spotify(auth=token)


    # Remover as palavras dos titulos que o spotify não contem, como 'Official Music Video'
    def filterList(self, trackList):
        keywords = self.getKeywords()
        filteredTrackList = {"Filtered":[], "NotFiltered":[]} #Adiciono a este array as musicas filtradas pelas keywords
        for track in trackList:
            if any(word in track for word in keywords["keywords"]):
                for keyword in keywords["keywords"]:
                    if track.find(keyword) > -1: #Se encontrar a string de y->(keywords["keywords"]) dentro de x->(track) o valor ira ser > -1
                        trackFiltered = str(track).replace(str(keyword), '').strip()
                        if any(word in trackFiltered for word in keywords["splits"]):
                            for split in keywords["splits"]:
                                if trackFiltered.find(split) > -1:  # Se encontrar a string de y->(keywords["splits"]) dentro de x->(title) o valor ira ser > -1
                                    artist = trackFiltered.split(split)[0]
                                    title = trackFiltered.split(split)[1]
                                    filteredTrackList["Filtered"].append({'title':str(title), 'artist':str(artist)})
            else:
                filteredTrackList["NotFiltered"].append({'youtube-name':str(track)})
        return filteredTrackList

    #Procurar musicas do youtube no spotify
    def search(self, trackList):
        trackFound = ''
        trackFiltered = self.filterList(trackList)

        #Separo o titulo com palavras como 'ft.', 'feat.', '-' etc...
        # Fazer split do nome com separadores
        data = {"Found":[],"NotFound":[]}

        #1º - Pesquisar os tracks que foram filtrados
        for track in trackFiltered["Filtered"]:
            #print(track["artist"] + ' | ' + track["title"])

            #Pesquiso a track mais o artista
            query = self.Spotify.search(q=(track["artist"] + ' ' + track["title"]), limit=50)

            #Caso a query retorne 0 resultados
            if query["tracks"]["total"] == 0:
                query = self.Spotify.search(q=(track["title"]), limit=50)
            # Procurar no resultado da query retorna uma track com o mesmo nome e com o mesmo artista
            for trackItems in query["tracks"]["items"]:
                trackFound = fuzz.ratio(str(trackItems["name"]).lower(), str(track["title"]).lower())>75

                if not(trackFound):
                    trackFound = fuzz.ratio(str(trackItems["name"]).lower(), str(track["title"] + ' ' + track["artist"])) > 40
                trackFoundWithArtist = fuzz.ratio(str(trackItems["name"] + ' ' + trackItems["artists"][0]["name"]).lower(), str(track["title"] + " " +track["artist"]).lower()) > 90

                if trackFound:
                    for artist in trackItems["artists"]:
                        artistFound = fuzz.ratio(str(artist["name"]).lower(),str(track["artist"]).lower()) > 75
                        if not artistFound:
                            artistFound = str(artist["name"]).lower().__contains__(str(track["artist"]).lower())
                        else:
                            break

                    if artistFound:
                        data["Found"].append({"id": trackItems["id"], "title":track["title"], "artist":track["artist"]})
                        break

            if not(trackFound):
                data["NotFound"].append({"title":track["title"], "artist":track["artist"]})
        #Pesquisar titulos que não foram filtrados (maior parte não existirá no spotify)
        for track in trackFiltered["NotFiltered"]:
            #print(track['youtube-name'])
            # Pesquiso com o nome do youtube
            query = self.Spotify.search(q=track["youtube-name"])

            # Caso a query retorne zero resultados
            if query["tracks"]["total"] != 0:
                for trackItems in query["tracks"]["items"]:
                    trackFoundName = fuzz.ratio(str(trackItems["name"]),(str(track["youtube-name"]).lower())) > 90
                    trackFoundAll = fuzz.ratio(str(trackItems["name"] + ' ' + trackItems["artists"][0]["name"]), (str(track["youtube-name"]).lower())) > 90

                    if trackFound:
                        data["Found"].append({"id": trackItems["id"], "youtube-name": track["youtube-name"]})
                        break
                    else:
                        data["NotFound"].append({"youtube-name": track["youtube-name"]})
                        break
            else:
                data["NotFound"].append({"youtube-name": track["youtube-name"]})
        return data

    #Criar playlist com musicas que foram filtradas
    def createPlaylistWithTracks(self):

        if fuzz.ratio(self.public, 'Yes') > 30:
            self.public = True
        else:
            self.public = False

        if len(self.playlistName) == 0:
            self.playlistName = 'Created Playlist'

        #Request da playlist do youtube
        playlist = UtilYoutube(playlistId=self.playlistId).getList()

        print("A extrair os titulos...")
        #Extrair apenas os titulos das musicas da playlist
        ytTitles = []
        for x in playlist['items']:
            ytTitles.append(x['snippet']['title'])

        print("A procurar no spotify...")
        #Procurar os titulos do youtube no spotify
        playlist = self.search(ytTitles)

        print("A criar a sua playlist...")
        #Criar uma playlist com as informações inseridas pelo utilizador
        createdPlaylist = self.Spotify.user_playlist_create(user=self.user["id"], name=self.playlistName, public=self.public, description=self.description)

        # Passar o id, para um array, das musicas encontradas no spotify
        spotifyTrackId = []
        for track in playlist["Found"]:
            spotifyTrackId.append(track["id"])

        print("A adicionar musicas a sua nova playlist")
        #Adicionar as músicas pelo id
        self.Spotify.user_playlist_add_tracks(user=self.user["id"], playlist_id=createdPlaylist["id"], tracks=spotifyTrackId)

        #Anotar e informar quais os titulos que não foram encontrados no spotify.
        fileName = "Musics not found.txt"
        print("ATENÇÃO: Algumas músicas não foram encontradas, encontram-se no ficheiro: " + fileName)
        open(fileName, "w").close() #Create an empty file
        with open(fileName, "a", encoding="utf-8") as file:
            for track in playlist["NotFound"]:
                if "youtube-name" in track:
                    file.write(track["youtube-name"] + '\n')
                else:
                    file.write(track["artist"] + ' - ' + track["title"] + '\n')




        return "Lista criada com sucesso!"






