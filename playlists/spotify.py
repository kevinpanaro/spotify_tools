import requests
import json
import spotipy
import spotipy.util as util
import re
import sys

class Spotify:

    def __init__(self, user_id, scope, client_id, client_secret):
        self._user_id = user_id
        self._scope = scope
        self._client_id = client_id
        self._client_secret = client_secret
        self.get_token()
        self.get_user_playlists()

    def get_token(self):
        '''validation token. also look for .cache file'''
        self.token = util.prompt_for_user_token(self._user_id, self._scope, self._client_id, self._client_secret, 'http://localhost/')
        self.sp = spotipy.Spotify(auth=self.token)

    def _get_playlist_id(self, playlist_name):
        '''Returns the id of a specific playlist'''
        for playlist in self.all_playlists:
            if playlist['name'] == playlist_name:
                return(playlist['id'])

    def _get_playlist_info(self, playlist_name):
        for playlist in self.all_playlists:
            if playlist_name == playlist['name']:
                self._user_requested_playlist = playlist

        try:
            results = self.sp.user_playlist(self._user_id, self._user_requested_playlist['id'], fields="tracks,next")
        except:
            try:
                results = (self._user_requested_playlist['owner']['id'], self._user_requested_playlist['id'])
            except:
                results = None
        return(results)


    def set_trace(self, trace=False):
        self.sp.trace = trace

    def total_user_playlists(self):
        playlist = self.sp.current_user_playlists(limit=1, offset=0)
        return(playlist['total'])

    def get_user_playlists(self, offset=0):
        if offset == 0:
            self.playlist_names = []
            self.all_playlists = []
        playlists = self.sp.current_user_playlists(limit=50, offset=offset)
        for playlist in playlists['items']:
            self.all_playlists.append(playlist)
            self.playlist_names.append(playlist['name'])
        if playlists['next']:
            return(self.get_user_playlists(offset=offset+50))
    

    def show_playlists(self):
        for playlist in self.playlist_names:
            print(playlist)


    def export_playlist(self, playlist_name, filename="spotify_playlists.json"):
        try:
            with open(filename, encoding='utf-8') as f:
                current_file = json.load(f)
        except FileNotFoundError:
            with open(filename, 'w', encoding='utf-8') as f:
                current_file = {}

        if ~isinstance(playlist_name, list):
            playlist_name = list(playlist_name)

        remove_these = [item for item in list(current_file.keys()) if item not in playlist_name]

        current_file = {key: value for key, value in current_file.items() if key not in remove_these}

        playlist_name = [playlist for playlist in playlist_name if playlist not in current_file.keys()]
        
        if playlist_name == ["@n3idf#0b)-ad09en*5^"]:
            print("All export")
            playlist_name = self.playlist_names

        for result in playlist_name:
            playlist_info = self._get_playlist_info(result)
            if playlist_info == None:
                print("{} does not exist".format(result))
                continue

            if isinstance(playlist_info, tuple):
                owner_id, playlist_id = playlist_info

                try:
                    non_user_playlists = current_file["non_user_playlists"]

                    if owner_id not in non_user_playlists:
                        non_user_playlists.append({owner_id: playlist_id})

                except KeyError:
                    current_file["non_user_playlists"] = [{owner_id: playlist_id}]
                continue

            all_tracks = playlist_info['tracks']['items']
            for track in all_tracks:
                track_id = track['track']['id']
                try:
                    current_file[result].append(track_id)
                except KeyError:
                    current_file[result] = [track_id]

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(current_file, f)

    def import_playlist(self, filename="spotify_playlists.json"):
        try:
            with open(filename, encoding='utf-8') as f:
                playlists = json.load(f)
        except:
            print("{} does not exist".format(filename))
            return

        playlist_names = list(playlists.keys())
        for playlist_name in playlist_names:
            if playlist_name == "non_user_playlists":
                print(playlists[playlist_name])
                for element in playlists[playlist_name]:
                    owner_id, playlist_id = (list(element.items())[0])
                    if self.sp.user_playlist_is_following(owner_id, playlist_id, [self._user_id])[0]:
                        print("{} is already following {} by {} ".format(self._user_id, playlist_id, owner_id))
                    else:
                        self.sp.user_playlist_follow_playlist(owner_id, playlist_id)
                        print("{} is now following {} by {} ".format(self._user_id, playlist_id, owner_id))
                    continue
                continue

            playlist_uris = playlists[playlist_name]

            if playlist_name in self.playlist_names:
                print("Playlist, {0:10}, already exists in user, {1:10}, library".format(playlist_name, self._user_id))
                continue

            self.sp.user_playlist_create(self._user_id, playlist_name)
            self.get_user_playlists()
            playlist_id = self._get_playlist_id(playlist_name)
            self.sp.user_playlist_add_tracks(self._user_id, playlist_id, playlist_uris)
            print("Playlist, {0:10}, added to user, {1:10}, library".format(playlist_name, self._user_id))
                

    class SpotifyError(Exception):
        pass

class SpotifyCLI:
    def __init__(self):
        with open('creds.json', encoding='utf-8') as f:
            creds = json.load(f)
        self.me = Spotify('12120187843','playlist-read-collaborative playlist-read-private playlist-modify-public playlist-modify-private', creds['client_id'], creds['client_secret'])
        self.user_input = None
        self.intro()

    def user_prompt(self, func_call, *args):
        valid = False
        while not valid:
            for li, item in enumerate(args):
                print("[{}] {}".format(li+1, item))
            self.user_input = int(input("Input: ")) - 1
            valid = self.handle_input(args)
        func_call()

    def imp_exp(self):
        if self.user_input == 0:
            print("Export")
            self.user_prompt(self.null, "Export All", "Manually enter playlists")
            if self.user_input == 0:
                playlist_names = ["@n3idf#0b)-ad09en*5^"] # "password" 
            elif self.user_input == 1:
                playlist_name = " "
                playlist_names = []
                while playlist_name != "":
                    playlist_name = input("Enter Playlist Name, or press enter to finish: ")
                    if playlist_name != "":
                        playlist_names.append(playlist_name)

            save_file = input("Enter save filename (enter for default): ") + ".json"
            
            if save_file == ".json":
                self.me.export_playlist(playlist_names)
            else:
                self.me.export_playlist(playlist_names, save_file)

        elif self.user_input == 1:
            save_file = input("Enter save filename (enter for default): ") + ".json"
            if save_file == ".json":
                self.me.import_playlist()
            else:
                self.me.import_playlist(save_file)

    def confirm(self, selection):
        ''' not implimented'''
        user_input = "You selected " + selection + " - Is this correct (y/n)"
        if user_input.lower() == 'y':
            return(True)
        else:
            print("Stopping")
            return(False)

    def handle_input(self, valid_input):
        try:
            if self.user_input in range(len(valid_input)):
                return(True)
            else:
                raise Exception
        except:
            print("\nInvalid Input, Try again")
            return(False)


    def execute_command(self):
        if int(self.user_input) == 1:

            playlist_name = " "
            playlist_names = []
            while playlist_name != "":
                playlist_name = input("Enter Playlist Name, or press enter to finish: ")
                if playlist_name != "":
                    playlist_names.append(playlist_name)

            if len(playlist_names) == 0:
                playlist_names = ["ALL_PLAYLISTS"]
            save_file = input("Enter save filename (enter for default): ") + ".json"
            if save_file == ".json":
                self.me.export_playlist(playlist_names)
            else:
                self.me.export_playlist(playlist_names, save_file)

        elif int(self.user_input) == 2:
            save_file = input("Enter save filename (enter for default): ") + ".json"
            if save_file == ".json":
                self.me.import_playlist()
            else:
                self.me.import_playlist(save_file)
        return



    def intro(self):
        print("Spotify CLI - Playlist Manager")
        self.user_prompt(self.imp_exp, "Export", "Import")


    def null(self):
        pass

def spotify():

    try:
        SpotifyCLI()
    except KeyboardInterrupt:
        print("goodbye")
    # me.set_trace(False)
    # me.get_user_playlists()

    # print(me.total_user_playlists())

    # me.show_playlists()

    # me.export_playlist(['mytj', 'Bass Gaming'])

    # me.import_playlist()

    # me._get_playlist_info('Bass Gaming')
    # print(me.get_playlist_uri('mytj'))

if __name__ == '__main__':
    spotify()