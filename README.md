`Description`: This script is for uploading and upgrading IOS images on Cisco routers and switches. It also saves running-config of each device being run against in `run_conf` folder.  

`Authors`: Sasank Tummalapalli      


* Instructions:  
```  
python3 Cisco_Upgrade - for instructions  
```  

This project is managed by Chef and can be found on jump servers in the folder `/opt/device-ios-upgrade/`  
* To add new image for another device's model, in `config.json`:   
  - {  
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"cisco/juniper MODEL_NAME" (required):  
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{  
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"image": "IMAGE_NAME" (required),  
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"md5": "MD5_OF_IMAGE" (required),  
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"sha512": "sha512_OF_IMAGE" (not required)  
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}  
    }   
* Image files have to be placed in `NSG_Storage/cisco-images/ios-Upgrade`  
