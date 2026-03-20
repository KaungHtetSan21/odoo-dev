# Auth Provider Module

## Setup Instruction
1. Build pip3 pyjwt and simplejson python package before install this module.
2. Download and Install jwt_provider module.
3. Go to Top right corner -> click on Group menu -> Inside the menu bar Click on-  key config menu ->
   set the access key and refresh key.
   Note:- You can not add more than one record inside key config.
4. Create a Group by giving these field details.
5. It will auto-generate a API Key . Using the API Key and API User password a third party user/application can
   login to Odoo and also make GET and POST API request to Odoo.    
6. The generated JWT tokens are stored inside the Users menu.

## Documentation
1. First Create a Group inside the App.
2. Take the API Key and API User Password and fill inside the JSON body. 

    API Url : http://{Paste Your BaseURl}/api/v1/login
    {
        "jsonrpc": "2.0",
        "params": {
            "api_key": "Paste-API-Key",
            "password": "Paste-API-User-Password"
        }
    }
    content-type : application/json
    
    -> Inside the API response body, You will get two JWT tokens - access token  and  refresh token.

3. Since the access token is expired, User/client can generate another access token by providing the refresh token 
   inside the Authorization header of Bearer Token.

    API Url : http://{Paste Your BaseURl}/api/v1/refresh
    {
        "jsonrpc": "2.0",
        "params": {}
    }
    content-type : application/json

    -> Inside the API response body, you will get a new Access Token.

4. Create Group record inside Group user model.
   
    API Url : http://{Paste Your BaseURl}/api/v1/create-group
    {
        "jsonrpc": "2.0",
        "params": {
            "group_name":  "Enter Group Name",
            "group_email": "Enter Group Email",
            "group_phone": "Enter Group Phone",
            "group_api_user_password":"ASdf45#$Sdd"
        }
    }
    content-type : application/json

5. Fetch Group record from Group user model.

    API Url : http://{Paste Your BaseURl}/api/v1/get-group
    {
        "jsonrpc": "2.0",
        "params": {}
    }
    content-type : application/json
     
    (Use Postman)
