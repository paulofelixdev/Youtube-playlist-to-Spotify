from utilSpotify import UtilSpotify
"""playlistName = input("Enter the desired playlist name: ")
description = input("Enter a description: ")
playlistId = input("Enter your youtube playlist ID: ")
public = input("Make it public? (Yes / No) ")"""



Spotify = UtilSpotify(playlistName="playlistName", playlistId="playlistId", public="public", description="description")
Spotify.createPlaylistWithTracks()