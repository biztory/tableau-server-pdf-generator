# Python Script to create PDF from dashboard based on parameters
## Importing libraries and features
import os, argparse, keyring, re, configparser, warnings, urllib, requests, shutil, json
from fpdf import FPDF
import datetime
from getpass import getpass
from pathlib import Path
warnings.filterwarnings('ignore')
config = configparser.ConfigParser()
config.read(r".\supplier_pdf_download.cfg")
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
def query_view_image(site_id, token, view_id, supplier, filename):
    if supplier == '':
        response = requests.get(
            URL + '/sites/{}/views/{}/image?maxAge=1'.format(site_id, view_id), 
            stream=True, verify=False, 
            headers={'Accept': 'application/json',
                    'X-Tableau-Auth': token}
        )
        status = check_error(response, "query_view_image")
        with open(filename, 'wb') as f:
            for chunk in response:
                f.write(chunk)
    else:
        response = requests.get(
            URL + '/sites/{}/views/{}/image?maxAge=1&vf_Select+Supplier={}'.format(site_id, view_id,urllib.parse.quote_plus(supplier)), 
            stream=True, verify=False, 
            headers={'Accept': 'application/json',
                    'X-Tableau-Auth': token}
        )
        status = check_error(response, "query_view_image")
        with open(filename, 'wb') as f:
            for chunk in response:
                f.write(chunk)
    return response
	

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
def gen_pdf(supplier_name, supplier_num, week_number, file_loc, datepart_filename, num_views):
    if supplier_name == '':
        print("Developing PDF ...")
        pdf = FPDF(orientation = 'L', unit = 'mm', format = 'A4')
        pdf.set_left_margin(8)
        for count in range(1,num_views+1):
            pdf.add_page()
            pdf.image(r'{}\temp_{}.png'.format(file_loc, count), x=8, y=8, w=282)

        filename = r'{}\{}.pdf'.format(file_loc, datepart_filename)
        pdf.output(filename)
        print("Saved pdf as {}".format(filename))
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write("\n{} Saved pdf as {}!".format(current_timestamp, filename))
        
    else:
        print("Developing PDF for {}...".format(supplier_name))
        for chars in illegal_chars:
            supplier_name = supplier_name.replace(chars, '#')
        pdf = FPDF(orientation = 'L', unit = 'mm', format = 'A4')
        pdf.set_left_margin(8)
        for count in range(1,num_views+1):
            pdf.add_page()
            pdf.image(r'{}\temp_{}.png'.format(file_loc, count), x=8, y=8, w=282)

        filename = r'{}\{}-{}-{}.pdf'.format(file_loc, datepart_filename, supplier_num, supplier_name)
        pdf.output(filename)
        print("Saved pdf for Supplier {} as {}".format(supplier_name, filename))
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write("\n{} Saved pdf for Week {} for Supplier {}!".format(current_timestamp, week_number, supplier_name))
	

### Fn to iterate over views and save images
def iterate_views(site_id, token, view_ids, supplier_dict, week_number, file_loc, datepart_filename):
    if supplier_dict == '':
        count = 0
        for view in view_ids:
            count+=1
            query_view_image(site_id, token, view, '', r"{}\temp_{}.png".format(file_loc, count))
        gen_pdf('', '', week_number, file_loc, datepart_filename, count)
    else:
        for supplier in supplier_dict:
            print("\n\nBeginning to retrieve dashboards for {}".format(supplier))
            count = 0
            for view in view_ids:
                count+=1
                query_view_image(site_id, token, view, supplier,r"{}\temp_{}.png".format(file_loc, count))
            gen_pdf(supplier, supplier_dict[supplier], week_number, file_loc, datepart_filename, num_views)


### Fn to parse out supplier list from view
def parse_supply_list(site_id, token, supplier_workbook, supplier_view):
    supplier_workbook_response = query_workbooks_site(site_id, token, urllib.parse.quote_plus(supplier_workbook))
    supplier_view_id = query_workbook(site_id, token, supplier_workbook_response['workbooks']['workbook'][0]['id'], gen_views_list(supplier_view))[0]
    supplier_list = query_view_data(site_id, token, supplier_view_id[0])
    ret_supply_list = {}
    for supplier in supplier_list:
        temp = supplier.split(',')
        ret_supply_list[temp[0]] = temp[1]
    return ret_supply_list


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


### Fn to create a string with supplier list to place in configuration file
def supply_supplier_string(supplier_filename):
    supply_list = open(supplier_filename,'r')
    suppliers = supply_list.readlines()
    suppliers_str = ""
    for supply in suppliers:
        temp = supply.split("\t")
        temp[0] = temp[0].lstrip()
        temp[0] = temp[0].rstrip()
        temp[0] = '"{}"'.format(temp[0])
        temp[1] = temp[1].lstrip()
        temp[1] = temp[1].rstrip()
        temp[1] = temp[1].replace(".","")
        suppliers_str = suppliers_str + temp[0] + ":" + temp[1] + ","
    suppliers_str = suppliers_str[:-1]
    suppliers_str = "{"+suppliers_str+"}"
    print(suppliers_str)
	

## Variables
server = config["server_connection"]["server"] # Enter site in format tableau.company.com without the https before it
site_content_url = config["server_connection"]["site"] # This can be found from the URL of the content and if using the Default site then this will be blank
api_ver = config["server_connection"]["api"] # This can be found from the Tableau Server REST API reference
URL = "https://{}/api/{}".format(server, api_ver)
    

##Parsing arguments, checking login method and signing into Server
parser = argparse.ArgumentParser(prog="tableau-generate-pdf", description="Generate PDFs for suppliers based on the config file")
if config["server_connection"]["loginmethod"] == 'PAT':
    parser.add_argument("--tableau-username", "-u", dest="tableau_username",  default ="", required=False, type=str, help="Valid Personal Access Token name for a user who can create PDFs for the supplier.")
    parser.add_argument("--password", "-p", dest="password", default ="", required=False, type=str, help="Valid Personal Access Token for user (defaults to checking the configuration file)")
    args = parser.parse_args()
    username = args.tableau_username  # This is your username
    password = args.password
    if username == "":
        username = config["auth_details"]["authname"]
    if password == "":
        password = config["auth_details"]["auth"]
    site_id, token = sign_in_pat(username, password, site_content_url)
    if token == 0:
        exit()
elif config["server_connection"]["loginmethod"] == 'Local':
    if config["auth_details"]["authname"] == "":
        parser.add_argument("--tableau-username", "-u", dest="tableau_username", default ="", required=True, type=str, help="Username of a user who can create PDFs for the supplier.")
        parser.add_argument("--password", "-p", dest="password", default ="", required=False, type=str, help="Password for user (defaults to prompting user)")
        args = parser.parse_args()
        username = args.tableau_username  # This is your username
        password = args.password
        if password == "":
            password = getpass("Enter your password for the Tableau Server: ")
        site_id, token = sign_in(username, password, site_content_url)
        if token == 0:
            exit()

    else:
        parser.add_argument("--tableau-username", "-u", dest="tableau_username", default ="", required=False, type=str, help="Username of a user who can create PDFs for the supplier.")
        parser.add_argument("--password", "-p", dest="password", default ="", required=False, type=str, help="Password for user (defaults to prompting user)")
        args = parser.parse_args()
        username = args.tableau_username  # This is your username
        password = args.password
        if username == "":
            username = config["auth_details"]["authname"]
        if password == "":
            password = config["auth_details"]["auth"]
        site_id, token = sign_in(username, password, site_content_url)
        if token == 0:
            exit()

else:
    parser.add_argument("--tableau-username", "-u", dest="tableau_username", required=True, type=str, help="Username of a user who can create PDFs for the supplier.")
    parser.add_argument("--password", "-p", dest="password", default ="", required=False, type=str, help="Password for user (defaults to prompting user)")
    args = parser.parse_args()
    username = args.tableau_username  # This is your username
    password = args.password
    if password == "":
        password = getpass("Enter your password for the Tableau Server: ")
    site_id, token = sign_in(username, password, site_content_url)
    if token == 0:
        exit()


## Find Suppliers from view
#supplier_list = parse_supply_list(site_id, token, config["supplier_list"]["supplier_list_workbook"], config["supplier_list"]["supplier_list_view"])
        

## Find workbook id from name
workbook_response = query_workbooks_site(site_id, token, urllib.parse.quote_plus(config["workbook_details"]["workbookname"]))


## Iterate over views and create PDFs
datepart_filename = create_date_filename()
iterate_views(site_id, token, query_workbook(site_id, token, workbook_response['workbooks']['workbook'][0]['id'], gen_views_list(config["workbook_details"]["viewnames"]))[0], '', datetime.date.today().strftime("%V"),  config["workbook_details"]["download_loc"], datepart_filename)


## Close files and sign out of server
log_file.close()
sign_out(site_id, token)