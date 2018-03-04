import os
from sodapy import Socrata
from datetime import datetime, timedelta
from dotenv import get_key, find_dotenv
import requests
import csv
import pandas as pd
import math


APP_TOKEN = get_key(find_dotenv(), 'SODAPY_APPTOKEN')

DOMAIN = 'https://data.cityofchicago.org'


historicals = [{'service_name':'potholes',
                'clean_cols': {'CREATION DATE': 'creation_date', 
                               'STATUS': 'status', 
                               'COMPLETION DATE': 'completion_date', 
                               'SERVICE REQUEST NUMBER': 'service_request_number', 
                               'TYPE OF SERVICE REQUEST': 'type_of_service_request', 
                               'CURRENT ACTIVITY': 'current_activity', 
                               'MOST RECENT ACTION': 'most_recent_action',
                               'NUMBER OF POTHOLES FILLED ON BLOCK': 'number_of_potholes_filled_on_block',
                               'STREET ADDRESS': 'street_address', 
                               'ZIP': 'zip', 
                               'X COORDINATE': 'x_coordinate', 
                               'Y COORDINATE': 'y_coordinate', 
                               'Ward': 'ward', 
                               'Police District': 'police_district', 
                               'Community Area': 'community_area', 
                               'SSA': 'ssa', 
                               'LATITUDE': 'latitude', 
                               'LONGITUDE': 'longitude', 
                               'LOCATION': 'location'},                                               
                'url': 'https://data.cityofchicago.org/api/views/7as2-ds3y/rows.csv?accessType=DOWNLOAD&api_foundry=true',
                'final_indicator': 'Final Outcome',
                'endpoint':'787j-mys9'},
               {'service_name': 'rodents',
                'clean_cols': {'Creation Date': 'creation_date',
                               'Status': 'status',
                               'Completion Date': 'completion_date',
                               'Service Request Number': 'service_request_number',
                               'Type of Service Request': 'type_of_service_request',
                               'Number of Premises Baited': 'number_of_premises_baited',
                               'Number of Premises with Garbage': 'number_of_premises_with_garbage',
                               'Number of Premises with Rats': 'number_of_premises_with_rats',
                               'Current Activity': 'current_activity',
                               'Most Recent Action': 'most_recent_action',
                               'Street Address': 'street_address',
                               'ZIP Code': 'zip',
                               'X Coordinate': 'x_coordinate',
                               'Y Coordinate': 'y_coordinate',
                               'Ward': 'ward',
                               'Police District': 'police_district',
                               'Community Area': 'community_area',
                               'Latitude': 'latitude',
                               'Longitude': 'longitude',
                               'Location': 'location'}, 
                'url': 'https://data.cityofchicago.org/api/views/97t6-zrhs/rows.csv?accessType=DOWNLOAD&api_foundry=true',
                'final_indicator': 'Dispatch Crew',
                'endpoint': 'dvua-vftq'},
               {'service_name': 'streetlights',
                'clean_cols': {'Creation Date': 'creation_date',
                                'Status': 'status',
                                'Completion Date': 'completion_date',
                                'Service Request Number': 'service_request_number',
                                'Type of Service Request': 'type_of_service_request',
                                'Street Address': 'street_address',
                                'ZIP Code': 'zip',
                                'X Coordinate': 'x_coordinate',
                                'Y Coordinate': 'y_coordinate',
                                'Ward': 'ward',
                                'Police District': 'police_district',
                                'Community Area': 'community_area',
                                'Latitude': 'latitude',
                                'Longitude': 'longitude',
                                'Location': 'location'},
                'url': 'https://data.cityofchicago.org/api/views/3aav-uy2v/rows.csv?accessType=DOWNLOAD&api_foundry=true',
                'final_indicator': None,
                'endpoint': 'h555-t6kz'}
                ]

    #     # note for streetlight, location is a text field rather than point, so
    #     # within_circle cannot be used
    #  


def convert_dates(date_series):
    """
    Faster approach to datetime parsing for large datasets leveraging repated dates.

    Source: https://github.com/sanand0/benchmarks/commit/0baf65b290b10016e6c5118f6c4055b0c45be2b0
    """
    dates = {date:pd.to_datetime(date) for date in date_series.unique()}
    return date_series.map(dates)


def build_initial_tables(historicals_list):
    '''
    Create databases for each of the 311 services stored as keys in a given
    dictionary, each of which is a dictionary indicating a related CSV URL and 
    column names.
    '''
    initial_records = []

    for service_dict in historicals_list:
        print("Starting: {}".format(service_dict['service_name']))
        try:
            r = requests.get(service_dict['url'])

            if r.status_code == 200:
                decoded_dl = r.content.decode('utf-8')
                print("decoded")
                req_reader = csv.reader(decoded_dl.splitlines(), delimiter = ',')
                print("read")
                read_info = list(req_reader)
                print("listed")
                historicals_df = pd.DataFrame(read_info[1:], columns = read_info[0])
                print("made dataframe")
                
                historicals_df.rename(columns = service_dict['clean_cols'], inplace=True)
                print("renamed")

                historicals_df['creation_date'] = convert_dates(historicals_df['creation_date'])
                historicals_df['completion_date'] = convert_dates(historicals_df['completion_date'])
                print("converted dates")

                historicals_df['response_time'] = historicals_df['completion_date'] - historicals_df['creation_date']
                
                
                initial_records.append(historicals_df)
                print("done, {:,} records".format(historicals_df.shape[0]))


        except:
            print("{}: Could not retrive CSV for {}".format(r.status_code, service_dict['service_name']))

    return initial_records



def dedupe_df(df, service_dict):
    dupes = df[df.duplicated(subset = 'service_request_number', keep = False)]
    print("Found {} request numbers with duplicates.".format(len(dupes['service_request_number'].unique())))
    df.drop_duplicates(subset = 'service_request_number', keep = False, inplace = True)
    
    dupe_list = dupes['service_request_number'].unique()
    keep_list = []
    final_trigger = service_dict['final_indicator']

    for duplicate in dupe_list:
        focus = dupes[dupes['service_request_number'] == duplicate]

        if not final_trigger:    
            # focus['completion_date'] = pd.to_datetime(x['completion_date'])
            most_recent = focus['completion_date'].idxmax()
            keep_list.append(most_recent)

        else:
            focus = dupes[dupes['service_request_number'] == duplicate]
            final = focus[focus['current_activity'] == final_trigger]
            
            if final.shape[0] == 1:
                final_outcome = final.index[0]
                keep_list.append(final_outcome)

            elif final.shape[0] > 1:
                # final['completion_date'] = pd.to_datetime(x['completion_date'])
                most_recent = final['completion_date'].idxmax()
                keep_list.append(most_recent)

            elif final.shape[0] == 0:
                # if none of the duplicate entries are noted as final steps
                # focus['completion_date'] = pd.to_datetime(x['completion_date'])
                most_recent = focus['completion_date'].idxmax()
                keep_list.append(most_recent)

    deduped_df = dupes.loc[keep_list]
    clean_df = df.append(deduped_df, ignore_index = True)
    clean_df.set_index(keys = 'service_request_number', inplace = True)

    return clean_df



def check_updates(service_dict, days_back = 1):
    period = datetime.now() - timedelta(days = days_back)
    period = period.date().isoformat() 
    offset_amt = 2000
    limit = 2000

    if service_dict['service_name'] == 'potholes':
        svc_req_number = 'SERVICE REQUEST NUMBER'
    else: 
        svc_req_number = 'Service Request Number'
   
    base_url = DOMAIN + "/resource/{}.json?$$app_token={}".format(service_dict['endpoint'], APP_TOKEN)
    test_url = base_url + "&$select=count(*)&$where=:updated_at>'{}'".format(period)
    update_url = base_url + "&$limit={}&$where=:updated_at>'{}'".format(limit, period)
    
    check_result = requests.get(test_url)
    print(test_url, "Code:", check_result.status_code)
    python_check = check_result.json()
    num_records = int(python_check[0]['count'])
    print(num_records)
    pulls = math.ceil(int(num_records) / limit)
    print(pulls)

    new_updates = requests.get(update_url)

    print(update_url, "Code:", new_updates.status_code)
    
    newly_updated = pd.DataFrame(new_updates.json())
    print("pull #: 1")
    print(newly_updated[:5])
    
    if pulls > 1:
        
        # perform HTTP GET request n - 1 more times and add to dataframe
        update_list = [newly_updated]
        for pull in range(pulls - 1):
            print("pull #:", pull + 2)
            offset_url = base_url + "&$limit={}&$offset={}&$where=:updated_at>'{}'".format(limit, offset_amt, period)
            offset_amt += 2000
           
            next_pull = requests.get(offset_url)
            print(offset_url, "Code:", next_pull.status_code)
            next_pull_df = pd.DataFrame(next_pull.json())

            update_list.append(next_pull_df)

            
        newly_updated = pd.concat(update_list, ignore_index = True)
    
    newly_updated.rename(columns = service_dict['clean_cols'], inplace=True)
    print(newly_updated[:5])
    newly_updated['creation_date'] = convert_dates(newly_updated['creation_date'])
    newly_updated['completion_date'] = convert_dates(newly_updated['completion_date'])

    return newly_updated



def daily_db_update(historicals_list): 
    all_updates = []
    for service_dict in historicals_list:
        updated = check_updates(service_dict)
        clean_updates = dedupe_df(updated, service_dict)
        all_updates.append(updated)
    return all_updates
    


def go():
    potholes, rodents, streetlights = build_initial_tables(historicals)
    clean_ph = dedupe_df(potholes, historicals)
    clean_rd = dedupe_df(rodents, historicals)
    clean_sl = dedupe_df(streetlights, historicals)
    
    return (potholes, rodents, streetlights)
 
