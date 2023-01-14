from datetime import datetime
import requests
import pandas as pd
import os
import sys
import loopleSheet as ls
import subprocess
from queue import Queue
import json
from operator import or_


class Twitch_stream_bot:
    """
    A class containing a subroutine which uses the Twitch API to look for french live streams with the VTuber tag.
    The matching streams are then stored locally in csv files.
    """
    def __init__(self):

        # The .json with the CLIENT_ID and the TOKEN
        with open(os.path.dirname(os.path.realpath(sys.argv[0])) + '/../twitch_credentials.json', mode='r') as f:
            twitch_credentials = json.load(f)

            # Twitch API variables
            CLIENT_ID = twitch_credentials['CLIENT_ID']
            TOKEN = twitch_credentials['TOKEN']


        self.vtuber_tag_id = '52d7e4cc-633d-46f5-818c-bb59102d9549'

        self.url = 'https://api.twitch.tv/helix/streams?type=live&language=fr&first=100'
        self.headers = {'Authorization':'Bearer ' + TOKEN, 'Client-Id':CLIENT_ID}

        self.csv_path = os.path.dirname(os.path.realpath(sys.argv[0])) + '/../Data/scattered/tagIds_tags/'


        # For finding new streams and just ended streams
        # According to the Twitch API, some streams can be missed (because indexing changes over time)
        # This is a redundancy system to reduce the probability of missing data.
        queue_len = 5
        self.vtuber_streams_queue = Queue()
        for i in range(queue_len):
            self.vtuber_streams_queue.put(pd.DataFrame(columns=['id']))

        self.nb_executions = 0

    def _filterVtuberStream(self, df):
        """
        Filter a DataFrame based on the presence of the Vtuber tag identifier or the word Vtuber in the tag list.

        Parameters
        ----------
        df : pandas.DataFrame
            The source data

        Return
        ------
        df_filtered : pandas.DataFrame
            A new DataFrame with just the matching rows
        """
        tag_ids_filter = [False]*df.shape[0]
        tags_filter = [False]*df.shape[0]

        if 'tag_ids' in df.columns:
            tag_ids_filter = df.tag_ids.map(lambda x: type(x) == list and self.vtuber_tag_id in x)

        if 'tags' in df.columns:
            tags_filter = df.tags.map(lambda x: type(x) == list and 'VTUBER' in map(str.upper, x))

        filter = list(map(or_, tag_ids_filter, tags_filter))
        return df[filter]
        
        

    def _getFrenchVtuberStreams(self):
        """
        Look for french streams with the VTuber tag using the Twitch API.

        At the moment, Twitch's API does not support getting streams by tags.
        So we are forced to get all french streams and then filter to keep only french streams with the VTuber tag.

        Return
        ------
        vtuber_streams : pandas.DataFrame
            The DataFrame with all the current live streams in french with a VTuber tag
        nb_pages : int
            The number of paginations traversed (one pagination contains 100 streams)
        """
        response = requests.get(self.url, headers=self.headers)
        df_response = pd.DataFrame(response.json()['data'])
        vtuber_streams = self._filterVtuberStream(df_response)

        nb_pages = 1

        # While there other pages to get
        while len(response.json()['pagination']) > 0:
            response = requests.get(self.url + '&after=' + response.json()['pagination']['cursor'], headers=self.headers)
            df_response = pd.DataFrame(response.json()['data'])
            
            df_filtered = self._filterVtuberStream(df_response)
                
            vtuber_streams = pd.concat([vtuber_streams, df_filtered], ignore_index=True)
            nb_pages += 1


        return vtuber_streams, nb_pages


    def subroutine(self, loopleSheet):
        """
        Subroutine provided to LoopleSheet and called automatically.

        To know which streams are new and which are already known by `Twitch_stream_bot`, all the french streams with a VTuber tag (new or not) found by the last execution of *subroutine* are stored in the RAM.
        Then comparing them with the streams found by the current execution of *subroutine* allows to point out the new streams and the streams which ended.
        Finally just the streams which ended are appended to the .csv file (enriched by the datetime of the end), thus forming a complete data set.
        """
        vtuber_streams, nb_pages = self._getFrenchVtuberStreams()

        vtuber_streams['_custom_ended_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        self.vtuber_streams_queue.put(vtuber_streams)
        older_vtuber_streams = self.vtuber_streams_queue.get()

        stable_vtuber_streams = pd.concat(list(self.vtuber_streams_queue.queue))
        
        stable_vtuber_streams = stable_vtuber_streams.groupby(['id']).apply(lambda df: df.iloc[0] if len(df) > 0 else None).reset_index(drop=True)

        id_difference_vtuber_streams = pd.concat([stable_vtuber_streams, older_vtuber_streams]).loc[:, ['id']].drop_duplicates(keep=False)
        ended_vtuber_streams = older_vtuber_streams.merge(id_difference_vtuber_streams)
        
        # mostly that but not the same id_difference_vtuber_streams => this difference : | (last_last... + last...) - vtuber_streams |
        # new_vtuber_streams = vtuber_streams.merge(id_difference_vtuber_streams)
        
        self._saveEndedVtuber(ended_vtuber_streams)

        print(f'{datetime.now().strftime("%d/%m %H:%M:%S")} - {vtuber_streams.shape[0]} french vtuber streams extracted (over {nb_pages} paginations of french streams)')
        print(f'Change : - {ended_vtuber_streams.shape[0]} / + ?')

            
        if self.nb_executions % 30 == 0:
            loopleSheet.post(f'{vtuber_streams.shape[0]} french vtuber streams (over {nb_pages} paginations)')
            subprocess.run(f'drive push --no-prompt {self.csv_path} > /dev/null', shell=True)

        self.nb_executions += 1


    def _saveEndedVtuber(self, ended_vtuber_streams):
        """
        Save dataframe to a .csv file. One .csv file for one day.
        """
        path = self.csv_path + 'data_twitch_vtuber_streams' + datetime.now().strftime("_%Y-%m-%d.csv")

        if os.path.exists(path):  
            ended_vtuber_streams.to_csv(path_or_buf=path, header=False, index=False, mode='a')
        else:
            ended_vtuber_streams.to_csv(path_or_buf=path, header=True, index=False, mode='w')



if __name__ == "__main__":
    # The .json with the Google account credentials is in the parent folder of the script
    ls.LoopleSheet(json_path=os.path.dirname(os.path.realpath(sys.argv[0]))+'/google_credentials.json',
    spreadsheet_id='1BhF_J82WbDO8cSh1Is49LsK0D_ZxP8qNvGLta4p-IUE',
    runnable=Twitch_stream_bot().subroutine,
    catchingExceptionsFromRunnable=True,
    errorStream='stderr').start()