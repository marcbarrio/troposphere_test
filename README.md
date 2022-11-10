# Comments

All these resources: **Subnet, VPC, Ec2 Instance & LoadBalancer** are created within the same CloudFormation Stack.

In a real environment those would be created within separate stacks (Different scripts for VPC, LoadBalancer, Ec2 instance) for when we need to change/remove any of them it would not affect to the rest.

For big templates like this one we could create a stack of python variables or stack parameters that would manage resource names, ip ranges,... or other important values.
Inside the Python script (template.py) there are several comments that explain each part and some thoughts.

# Creating the template

## Requirements
**Python3** and **troposphere module** have to be installed in the system.


## Generating the template

AWS Cloudformation accepts files in YAML or JSON as their creation scripts, troposphere lets you create in either. 
In order to generate the template to be used by AWS we have to execute the following command:

---

`$ python3 template.py `

---

The file template.py is set to generate both, JSON and YAML, for testing purposes even though only 1 of them is needed. Once the previous command has been executed 2 files will be created in the same directory:
**troposphere-exercise.json and troposphere-exercise.yaml** which we can use to generate our AWS Resources.

# Creating the AWS Resources

First we will need to create a KeyPair for our EC2 Instance to access via SSH. We can do this through the AWS Console EC2-->KeyPairs.

We can create our AWS Resources in 2 way.

- From the AWS Console: CloudFormation --> Stacks --> Create Stack. And Uploading our YAML or JSON file.
- From aws cli using the next command:

    `$ aws cloudformation create-stack --stack-name STACK_NAME --template-body file://troposphere-exercise.yaml --parameters keyname=KEYNAME_OF_KEYPAIR_CREATED`
    
    Besides, in order to use AWS cli we must install it and configure it following [this](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) steps.

# Deploying our app

Our app is made on a docker platform. In order to deploy it to our EC2 instance either we will have a CI/CD tool with a project configured to deploy and execute the docker compose script there. 

Or we do it manually, uploading the files in the "Docker" directory and executing:

`$ docker compose up -d `

Which will deploy our container mapping the port 80 of our host with the port 80 of that container that will be the one used by the web server (nginx) displaying the desired webpage. 

Since in our cloudformation script we already have declared and configured our Elastic Load Balancer with a default action redirecting the traffic to our EC2 Instance on port 80 we will only need to add to the DNS we use the CNAME of the ELB. 
There is a problem regarding the apex/root registry of a certain domain which can only be an A record. Since the AWS ELB does not have a static IP address we cannot use that registry to use as our app DNS. These are 2 of the simpler and cleaner solutions for this:

- We use another DNS registry as a CNAME to our ELB using a subdomain.
- We use Route53, the DNS Server service by AWS which lets you use "Aliases" that would redirect you to any of your AWS resources updating automatically that suposed A record to the proper IP that the ELB might have in every moment.

Once all this procedure is done we will be able to access our app via the DNS we have chosen and see the display of "Welcome to Cloud Platform Team!"