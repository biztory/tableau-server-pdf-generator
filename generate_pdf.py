# Python Script to create PDF from dashboard based on parameters
## Importing libraries and features
import os, argparse, keyring, re, configparser, warnings, urllib, requests, shutil, json
from fpdf import FPDF
import datetime
from getpass import getpass
from pathlib import Path
warnings.filterwarnings('ignore')
config = configparser.ConfigParser()
config.read(r".\tableau_server_pdf_generator.cfg")
illegal_chars = config["logging_details"]["illegalchars"].split(',')


## Open Log file
log_file_loc = r"{}\{}".format(str(Path.home()), config["logging_details"]["logfilename"])
log_file = open(log_file_loc, "a+")


## Functions
### Fn to check errors
def check_error(request, task):
    if task == "sign_in":
        if request.status_code == 200:
            print("\t\tUser signed in successfully!")
            return 1
        elif request.status_code == 404:
            print("\t\tERROR: User not found!!")
            return 0
        elif request.status_code == 401:
            print("\t\tERROR: Login error!!")
            return 0
        else:
            print("\t\tERROR: Request error check again!!")
            return 0
        
    elif task == "sign_out":
        if request.status_code == 204:
            print("\t\tUser signed out successfully!")
            return 1
        else:
            print("\t\tERROR: Request error check again!!")
            return 0
        
    elif task == "create_users":
        if request.status_code == 201:
            print("\t\tUser created successfully!")
            return 1
        elif request.status_code == 404:
            print("\t\tERROR: Site not found!!")
            return 0
        elif request.status_code == 409:
            print("\t\tERROR: User exists or license unavailable, check again!!")
            return 0
        elif request.status_code == 400:
            print("\t\tERROR: Invalid site role or bad request!!")
            return 0
        else:
            print("\t\tERROR: Request error check again!!")
            return 0
        
    elif task == "update_users":
        if request.status_code == 200:
            print("\t\tUser information updated successfully!")
            return 1
        elif request.status_code == 404:
            print("\t\tERROR: User or Site not found!!")
            return 0
        elif request.status_code == 409:
            print("\t\tERROR: User exists or license unavailable, check again!!")
            return 0
        elif request.status_code == 400:
            print("\t\tERROR: Invalid site role, email address or bad request!!")
            return 0
        elif request.status_code == 403:
            print("\t\tERROR: Licensing update on self or guest account not allowed!!")
            return 0
        else:
            print("\t\tERROR: Request error check again!!")
            return 0
        
    elif task == "find_group_id":
        if request.status_code == 200:
            print("\t\tGroup found!")
            return 1
        elif request.status_code == 404:
            print("\t\tERROR: Site not found!!")
            return 0
        else:
            print("\t\tERROR: Request error check again!!")
            return 0
        
    elif task == "add_user_group":
        if request.status_code == 200:
            print("\t\tUser added to group successfully!")
            return 1
        elif request.status_code == 404:
            print("\t\tERROR: Site or Group not found!!")
            return 0
        elif request.status_code == 409:
            print("\t\tERROR: Specified User already in group!!")
            return 0
        else:
            print("\t\tERROR: Request error check again!!")
            return 0
    elif task == "query_workbooks_site":
        if request.status_code == 200:
            print("\t\tQueried workbook name successfully!")
            return 1
        elif request.status_code == 400:
            print("\t\tERROR: Pagination error!!")
            return 
        elif request.status_code == 403:
            print("\t\tERROR: Forbidden to read workbook!!")
            return 0
        elif request.status_code == 404:
            print("\t\tERROR: Site or workbook not found!!")
            return 0
        else:
            print("\t\tERROR: Request error check again!!")
            return 0
    elif task == "query_view_image":
        if request.status_code == 200:
            print("\t\tQueried view image successfully!")
            return 1
        elif request.status_code == 403:
            print("\t\tERROR: Forbidden to view image!!")
            return 0
        elif request.status_code == 404:
            print("\t\tERROR: Site, workbook or view not found!!")
            return 0
        else:
            print("\t\tERROR: Request error check again!!")
            return 0
    elif task == "query_view_data":
        if request.status_code == 200:
            print("\t\tQueried view data successfully!")
            return 1
        elif request.status_code == 401:
            print("\t\tERROR: Invalid token!!")
            return 0
        elif request.status_code == 403:
            print("\t\tERROR: Forbidden to view data!!")
            return 0
        elif request.status_code == 404:
            print("\t\tERROR: Site, workbook or view not found!!")
            return 0
        else:
            print("\t\tERROR: Request error check again!!")
            return 0
			
			
### Fn to sign in to Server with a password
def sign_in(username, password, site=""):
    body = {
        "credentials": {
            "name": username,
            "password": password,
            "site": {
                "contentUrl": site
            }
        }
    }
    response = requests.post(
        URL + '/auth/signin', 
        json=body, 
        verify=False, 
        headers={'Accept': 'application/json'}
    )
    
    status = check_error(response, "sign_in")
    if status:
        return response.json()['credentials']['site']['id'], response.json()['credentials']['token']
    else:
        return 0,0
    

### Fn to sign in to Server with a PAT
def sign_in_pat(username, password, site=""):
    body = {
        "credentials": {
            "personalAccessTokenName": username,
            "personalAccessTokenSecret": password,
            "site": {
                "contentUrl": site
            }
        }
    }
    response = requests.post(
        URL + '/auth/signin', 
        json=body, 
        verify=False, 
        headers={'Accept': 'application/json'}
    )
    
    status = check_error(response, "sign_in")
    if status:
        return response.json()['credentials']['site']['id'], response.json()['credentials']['token']
    else:
        return 0,0



### Fn to sign out from Server
def sign_out(site_id, token):
    response = requests.post(
        URL + '/auth/signout', 
        verify=False, 
        headers={'Accept': 'application/json',
                'X-Tableau-Auth': token}
    )
    status = check_error(response, "sign_out")
    return status


### Fn to find workbook id
def query_workbooks_site(site_id, token, workbook_name):
    response = requests.get(
        URL + '/sites/{}/workbooks?filter=name:eq:{}'.format(site_id, workbook_name), 
        verify=False, 
        headers={'Accept': 'application/json',
                'X-Tableau-Auth': token}
    )
    status = check_error(response, "query_workbooks_site")
    return response.json()
	

### Fn to generate list of views
def gen_views_list(views_list):
    temp_views = views_list.split(',')
    views = []
    for item in temp_views:
        view_name = (item.lstrip()).rstrip()
        views.append(view_name)
    return views
	

### Fn to find view id
def query_workbook(site_id, token, workbook_id, views_list):
    response = requests.get(
        URL + '/sites/{}/workbooks/{}'.format(site_id, workbook_id), 
        verify=False, 
        headers={'Accept': 'application/json',
                'X-Tableau-Auth': token}
    )
    view_ids = []
    for view in response.json()['workbook']['views']['view']:
        if view['name'] in views_list:
            view_ids.append(view['id'])
    status = check_error(response, "query_workbook")
    return view_ids, status
	

### Fn to query view image
def query_view_image(site_id, token, view_id, filtername, filtervalue, filename, applyfilter, week_number):
    if applyfilter:
        response = requests.get(
            URL + '/sites/{}/views/{}/image?maxAge=1&vf_{}={}&vf_WeekDescr=Week+{}'.format(site_id, view_id, urllib.parse.quote_plus(filtername), urllib.parse.quote_plus(filtervalue), week_number), 
            stream=True, verify=False, 
            headers={'Accept': 'application/json',
                    'X-Tableau-Auth': token}
        )
    else:
        response = requests.get(
            URL + '/sites/{}/views/{}/image?maxAge=1'.format(site_id, view_id, week_number), 
            stream=True, verify=False, 
            headers={'Accept': 'application/json',
                    'X-Tableau-Auth': token}
        )

    status = check_error(response, "query_view_image")
    with open(filename, 'wb') as f:
        for chunk in response:
            f.write(chunk)
    return status
	

### Fn to query view data
def query_view_data(site_id, token, view_id):
    response = requests.get(
        URL + '/sites/{}/views/{}/data'.format(site_id, view_id), 
        verify=False, 
        headers={'Accept': 'application/json',
                'X-Tableau-Auth': token}
    ).text.splitlines()
    response.remove(response[0])
    #status = check_error(response, "query_view_data")
    return response


### Fn to generate pdf with images
def gen_pdf(filter_value_name, week_number, file_loc, datepart_filename, num_views):
    print("Developing PDF for {}...".format(filter_value_name))
    for chars in illegal_chars:
        filter_value_name = filter_value_name.replace(chars, '#')
    pdf = FPDF(orientation = 'L', unit = 'mm', format = 'A4')
    pdf.set_left_margin(8)
    for count in range(1,num_views):
        pdf.add_page()
        pdf.image(r'{}\temp_{}.png'.format(file_loc, count), x=8, y=8, w=282)
        
    filename = r'{}\{}-{}.pdf'.format(file_loc, datepart_filename, filter_value_name)
    pdf.output(filename)
    print("Saved pdf for filter_value {} as {}".format(filter_value_name, filename))
    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file.write("\n{} Saved pdf for Week {} for filter_value {}!".format(current_timestamp, week_number, filter_value_name))
	
### Fn to iterate over views and save images
def iterate_views_unfiltered(site_id, token, view_ids, week_number, file_loc, datepart_filename):
    run = True
    attempt = 0
    while (run == True):
        count = 1
        for view in view_ids:
            apply_filter = False
            view_image_code = query_view_image(site_id, token, view, '', '',r"{}\temp_{}.png".format(file_loc, count), False, week_number)
            count+=1
            if (view_image_code == 1):
                run = False
                attempt+=1
            else:
                if attempt > 3:
                    run = False
                else:
                    run = True
                    attempt+=1
                    break
        
    gen_pdf('All', week_number, file_loc, datepart_filename, count)


### Fn to iterate over views apply filters and save images
def iterate_views(site_id, token, view_ids, apply_filter_list, filter_value_list, week_number, file_loc, datepart_filename):
    for filter_value in filter_value_list:
        print("\n\nBeginning to retrieve dashboards for {}".format(filter_value))
        run = True
        attempt = 0
        while (run == True):
            count = 1
            for view in view_ids:
                if (view in apply_filter_list):
                    apply_filter = True
                    view_image_code = query_view_image(site_id, token, view, config["workbook_details"]["filtername"], filter_value,r"{}\temp_{}.png".format(file_loc, count), apply_filter, week_number)
                    count+=1
                    if (view_image_code == 1):
                        run = False
                        attempt+=1
                    else:
                        if attempt > 3:
                            run = False
                        else:
                            run = True
                            attempt+=1
                            break

                else:
                    apply_filter = False
                    view_image_code = query_view_image(site_id, token, view, config["workbook_details"]["filtername"], filter_value,r"{}\temp_{}.png".format(file_loc, count), apply_filter, week_number)
                    count+=1
                    if (view_image_code == 1):
                        run = False
                        attempt+=1
                    else:
                        if attempt > 3:
                            run = False
                        else:
                            run = True
                            attempt+=1
                            break

        gen_pdf(filter_value, week_number, file_loc, datepart_filename, count)


### Fn to parse out filter_value list from view
def parse_filter_list(site_id, token, filter_value_workbook, filter_value_view):
    filter_value_workbook_response = query_workbooks_site(site_id, token, urllib.parse.quote_plus(filter_value_workbook))
    filter_value_view_id = query_workbook(site_id, token, filter_value_workbook_response['workbooks']['workbook'][0]['id'], gen_views_list(filter_value_view))[0]
    filter_value_list = query_view_data(site_id, token, filter_value_view_id[0])
    return filter_value_list


### Fn to find year and week number
def create_date_filename():
    week = int(datetime.date.today().strftime("%V"))
    if week == 1:
        week = 52
        year = int(datetime.date.today().strftime("%Y"))-1
        date_part_filename = {}
    else:
        week-=1
        year = int(datetime.date.today().strftime("%Y"))
    return "{}{}".format(year, week)


### Fn to create a string with filter_value list to place in configuration file
def filter_filter_value_string(filter_value_filename):
    filter_list = open(filter_value_filename,'r')
    filter_values = filter_list.readlines()
    filter_values_str = ""
    for filter in filter_values:
        temp = filter.split("\t")
        temp[0] = temp[0].lstrip()
        temp[0] = temp[0].rstrip()
        temp[0] = '"{}"'.format(temp[0])
        temp[1] = temp[1].lstrip()
        temp[1] = temp[1].rstrip()
        temp[1] = temp[1].replace(".","")
        filter_values_str = filter_values_str + temp[0] + ":" + temp[1] + ","
    filter_values_str = filter_values_str[:-1]
    filter_values_str = "{"+filter_values_str+"}"
    print(filter_values_str)
	

## Variables
server = config["server_connection"]["server"] # Enter site in format tableau.company.com without the https before it
site_content_url = config["server_connection"]["site"] # This can be found from the URL of the content and if using the Default site then this will be blank
api_ver = config["server_connection"]["api"] # This can be found from the Tableau Server REST API reference
URL = "https://{}/api/{}".format(server, api_ver)
    

## Parsing arguments, checking login method and signing into Server
parser = argparse.ArgumentParser(prog="tableau-generate-pdf", description="Generate PDFs for filter_values based on the config file")
if config["server_connection"]["loginmethod"] == 'PAT':
    parser.add_argument("--tableau-username", "-u", dest="tableau_username",  default ="", required=False, type=str, help="Valid Personal Access Token name for a user who can create PDFs for the filter_value.")
    parser.add_argument("--password", "-p", dest="password", default ="", required=False, type=str, help="Valid Personal Access Token for user (defaults to checking the configuration file)")
    args = parser.parse_args()
    if args.tableau_username:
        username = args.tableau_username  # This is your username
        if username == "":
            username = config["auth_details"]["authname"]
    else:
        print("No username supplied, either supply as argument when running script or in config file")
        exit()
    if args.password:
        password = args.password
        if password == "":
            password = config["auth_details"]["auth"]
    else:
        password = getpass("Enter your PAT for the Tableau Server: ")
    site_id, token = sign_in_pat(username, password, site_content_url)
    if token == 0:
        exit()
elif config["server_connection"]["loginmethod"] == 'Local':
    parser.add_argument("--tableau-username", "-u", dest="tableau_username", default ="", required=False, type=str, help="Username of a user who can create PDFs for the filter_value.")
    parser.add_argument("--password", "-p", dest="password", default ="", required=False, type=str, help="Password for user (defaults to prompting user)")
    args = parser.parse_args()
    if args.tableau_username:
        username = args.tableau_username  # This is your username
        if username == "":
            username = config["auth_details"]["authname"]
    else:
        print("No username supplied, either supply as argument when running script or in config file")
        exit()
    if args.password:
        password = args.password
        if password == "":
            password = config["auth_details"]["auth"]
    else:
        password = getpass("Enter your password for the Tableau Server: ")
    site_id, token = sign_in(username, password, site_content_url)
    if token == 0:
        exit()
else:
    print("Incorrect login method specified in config file under server_connection > loginmethod! Login method has to be Local or PAT")
    exit()


## Find workbook id from name
workbook_response = query_workbooks_site(site_id, token, urllib.parse.quote_plus(config["workbook_details"]["workbookname"]))


## Find filter_values from view
if config["filter_value_list"]["filter_value_list_workbook"] == "":
    print("No filters applied")
else:
    print("Filters being applied...")
    filter_value_list = parse_filter_list(site_id, token, config["filter_value_list"]["filter_value_list_workbook"], config["filter_value_list"]["filter_value_list_view"])


## Iterate over views and create PDFs
datepart_filename = create_date_filename()
curr_week_number = datetime.date.today().isocalendar()[1] - 1
if config["filter_value_list"]["filter_value_list_workbook"] == "":
    print("Iterating over views with no filters...")
    iterate_views_unfiltered(site_id, token, query_workbook(site_id, token, workbook_response['workbooks']['workbook'][0]['id'], gen_views_list(config["workbook_details"]["viewnames"]))[0], curr_week_number, config["workbook_details"]["download_loc"], datepart_filename)
else:
    print("Iterating over views with filters applied...")
    iterate_views(site_id, token, query_workbook(site_id, token, workbook_response['workbooks']['workbook'][0]['id'], gen_views_list(config["workbook_details"]["viewnames"]))[0], query_workbook(site_id, token, workbook_response['workbooks']['workbook'][0]['id'], gen_views_list(config["workbook_details"]["applyfilters"]))[0], filter_value_list, curr_week_number,  config["workbook_details"]["download_loc"], datepart_filename)

## Close files and sign out of server
log_file.close()
sign_out(site_id, token)
