from datetime import datetime
import requests
import pandas as pd
import os
import sys
import loopleSheet as ls
import subprocess
import json


class Twitch_video_bot:
    """
    A class containing a subroutine (called by LoopleSheet) which uses the Twitch API to fetch all videos published by a broacaster who has used a Vtuber tag.
    The videos are then stored locally in csv files and pushed on Google Drive.
    """
    def __init__(self):

        # The .json with the CLIENT_ID and the TOKEN
        with open(os.path.dirname(os.path.realpath(sys.argv[0])) + '/../twitch_credentials.json', mode='r') as f:
            twitch_credentials = json.load(f)

            # Twitch API variables
            CLIENT_ID = twitch_credentials['CLIENT_ID']
            TOKEN = twitch_credentials['TOKEN']


        self.url = 'https://api.twitch.tv/helix/videos?first=100&user_id='
        self.headers = {'Authorization':'Bearer ' + TOKEN, 'Client-Id':CLIENT_ID}

        self.csv_path = os.path.dirname(os.path.realpath(sys.argv[0])) + '/../Data/scattered/videos/'


    def _get_user_videos(self, user_df):
        """
        Intended to be passed as a parameter to a pandas.core.groupby.generic.DataFrameGroupBy.apply call.
        It retrieves all videos published by the first row broadcaster.

        Parameters
        ----------
        user_df : pandas.DataFrame
            The DataFrame with data grouped by `user_id`

        Return
        ------
        df_response : pandas.DataFrame
            A new DataFrame with all the videos published by the user
        """
        user_id = user_df['user_id'].iloc[0]
        df_response = None
        
        try:
            response = requests.get(self.url + str(user_id), headers=self.headers)
            df_response = pd.DataFrame(response.json()["data"])

            if 'stream_id' not in df_response.columns and not df_response.empty:
                print(f"stream_id not in columns of user {user_id} - 1")
                return None

            # While there are other pages to get
            while len(response.json()["pagination"]) > 0 :
                    response = requests.get(self.url + str(user_id) + "&after=" + response.json()["pagination"]["cursor"], headers=self.headers)
                    df_new_response = pd.DataFrame(response.json()["data"])

                    if 'stream_id' not in df_new_response.columns and not df_new_response.empty:
                        print(f"stream_id not in columns of user {user_id} - 2")
                        return None

                    df_response = pd.concat([df_response, df_new_response])

            # If we're there it's because we got all pages without any error.
            # We can say that the work whith this user is done
            self.users_id_remaining.loc[self.users_id_remaining['user_id'] == user_id, 'videos_fetched'] = True
            
            return df_response                

        except Exception as e:
            print(f"Exception [{e}] with user {user_id}")
            return None

    def _get_users_id(self):
        """
        Gather all the user_id of the broadcasters that have used a Vtuber tag at least once since Twitch_stream_bot.py is running.
        Go through all the *scattered* csv and add the user_id found in each of them.
        The idea is to go through the *scattered* csv and not directly through the *aggregated* csv so that memory usage doesn't explode too much over time.
        
        Return
        ------
        users_id : pandas.DataFrame
            A DataFrame with a unique column *user_id* 
        """
        scattered_csv_paths = [os.path.dirname(os.path.realpath(sys.argv[0])) + '/../Data/scattered/tagIds/']
        scattered_csv_paths += [os.path.dirname(os.path.realpath(sys.argv[0])) + '/../Data/scattered/tagIds_tags/']
        
        users_id = pd.DataFrame()
        
        for scattered_csv_path in scattered_csv_paths:
            for file in os.listdir(path=scattered_csv_path):
                if file.endswith('csv'):
                    streams = pd.read_csv(scattered_csv_path + file)
                    if 'user_id' in streams.columns:
                        d_users_id = streams.loc[:, ['user_id']]
                        users_id = pd.concat([d_users_id, users_id]).drop_duplicates()

        return users_id

    def subroutine(self, loopleSheet):
        """
        Subroutine provided to LoopleSheet and called automatically.
        
        We only have to fetch the videos once a day.
        It first checks if the work has already been done and waits until at least 5am.

        If the work needs to be done, we get all the broadcasters, we retrieve all theirs videos and upload them.
        """
        path = self.csv_path + 'data_twitch_videos' + datetime.now().strftime("_%Y-%m-%d.csv")

        if os.path.exists(path) or datetime.now().hour < 5:
            return


        # It's time to work

        # Getting the broadcasters
        users_id = self._get_users_id()
        users_id['videos_fetched'] = False

        all_videos = pd.DataFrame()
        self.users_id_remaining = users_id

        # Retrieving videos with a redundancy system

        while self.users_id_remaining.shape[0] > 0:
            print(f'{datetime.now().strftime("%d/%m %H:%M:%S")} - {self.users_id_remaining.shape[0]} users remaining')
            new_videos = users_id.groupby('user_id').apply(self._get_user_videos).reset_index(drop=True)
            all_videos = pd.concat([new_videos, all_videos])
            self.users_id_remaining = self.users_id_remaining[self.users_id_remaining['videos_fetched'] == False]


        print(f'{datetime.now().strftime("%d/%m %H:%M:%S")} - {all_videos.shape[0]} videos fetched')    
        loopleSheet.post(f'{all_videos.shape[0]} videos fetched')

        
        all_videos.to_csv(path_or_buf=path, header=True, index=False, mode='w')

        #subprocess.run(f'drive push --no-prompt {self.csv_path} > /dev/null', shell=True)
            


if __name__ == "__main__":
    # The .json with the Google account credentials is in the parent folder of the script
    loopleSht = ls.LoopleSheet(json_path=os.path.dirname(os.path.realpath(sys.argv[0]))+'/google_credentials.json',
    spreadsheet_id='1BhF_J82WbDO8cSh1Is49LsK0D_ZxP8qNvGLta4p-IUE',
    runnable=Twitch_video_bot().subroutine,
    catchingExceptionsFromRunnable=True,
    errorStream='stderr')

    loopleSht.setGoogleSheetStructure(sleepTimeCell='B2', lastExecDateTimeCell='A5', messageColumn='E', msgDateColumn='F')
    loopleSht.start()