#!/usr/bin/python3

from __future__ import print_function

from troposphere import ec2
from troposphere import Tags, Ref, Sub, Export, ImportValue, Base64
from troposphere import Template, Output
from troposphere import elasticloadbalancingv2 as elb

###########Comments#############
#All these resources: Subnet, VPC, Ec2 Instance & LoadBalancer are created within the same CloudFormation Stack
#In a real environment those would be created within separate stacks for when we need to change/remove any of them it would not affect to the rest
################################



template = Template()

#Creation of VPC with CDIR Block 10.0.0.0/24 And a Tag name
vpc = template.add_resource(
    ec2.VPC(
        'VPC',
        CidrBlock="10.0.0.0/16",
        Tags=Tags(
            Name="VPC for troposphere exercise"
        )
    )
)

#Creation of Subnet with same CidrBlock as VPC and the VPC id from the previously created.
subnet = ec2.Subnet(
    "TestSubnet",
    AvailabilityZone="eu-west-3c",
    CidrBlock="10.0.0.0/24",
    VpcId=Ref(vpc),
    Tags=Tags(
        Name="Subnet for troposphere exercise",
        ZoneBlock="eu-west-3c (Paris) & 10.0.0.0/24"
    )
)

template.add_resource(subnet)

#Creating an output value to the subnet for hypothetical future use on other stacks
output_subnet = Output("outputSubnet")
output_subnet.Value = Ref(subnet)
output_subnet.Export = Export(Sub("${AWS::StackName}-" + subnet.title))

template.add_output(output_subnet)

#Creating a 2nd Subnet for the minimum required in the ELB
subnet2 = ec2.Subnet(
    "TestSubnet2",
    AvailabilityZone="eu-west-3a",
    CidrBlock="10.0.1.0/24",
    VpcId=Ref(vpc),
    Tags=Tags(
        Name="Subnet for ELB required input",
        ZoneBlock="eu-west-3a (Paris) & 10.0.1.0/24"
    )
)

template.add_resource(subnet2)

#Creating the EC2 instance to hold our application
ec2Instance = ec2.Instance("ApplicationInstance")
#Ubuntu 20.04LTS ami ID //Free tier elegible
ec2Instance.ImageId = "ami-064736ff8301af3ee"
#Instance type t2.micro 1vCPU 1GiB Mem //Free tier elegible
ec2Instance.InstanceType = "t2.micro"
# If the subnet creation and the ec2 instance creation would be done in separate stacks (which would be the way to go if the subnet was to be used by more AWS resources)
# we could add the value of the SubnetId with the Export output value we assigned to the subnet using the ImportValue function.
ec2Instance.SubnetId = Ref(subnet)
ec2Instance.Tags = [
    {"Key" : "Name", "Value" : "Ec2 instance to hold our application"},
    {"Key" : "Subnet", "Value" : "Belonging to the subnet 'TestSubnet'"}
]

#Using userdata for Ec2 to install Docker automatically since our application will be using docker.
userDataDockerInstall = """
    #!/bin/bash -xe
    sudo apt-get update
    sudo apt-get install ca-certificates curl gnupg lsb-release
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker ubuntu
"""

ec2Instance.UserData = Base64(userDataDockerInstall)

#Creating security group for the instance in order to be able to access the desired port (80 in this case, can change if exposed port from the docker container changes) from any ip
instancesg = ec2.SecurityGroup(
    "AppSecurityGroup",
    GroupDescription="Enable HTTP access to the instance",
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="80",
            ToPort="80",
            CidrIp="0.0.0.0/0"
        )
    ]
)
template.add_resource(instancesg)

ec2Instance.SecurityGroups = [Ref(instancesg)]
template.add_resource(ec2Instance)

#Creating the loadbalancer 
loadBalancer = elb.LoadBalancer(
    "ApplicationLoadBalancer",
    Name="ApplicationELB",
    Scheme="internet-facing",
    Subnets=[Ref(subnet),Ref(subnet2)],
    Tags=Tags(
        Name="ApplicationELB"
    )
)
template.add_resource(loadBalancer)

#Creating the target group for our application
appTargetGroup = elb.TargetGroup(
    "app80",
    HealthCheckIntervalSeconds="30",
    HealthCheckProtocol="HTTP",
    HealthCheckTimeoutSeconds="10",
    HealthyThresholdCount="4",
    Matcher=elb.Matcher(HttpCode="200"),
    Name="appTarget",
    Port="80",
    Protocol="HTTP",
    Targets=[
        elb.TargetDescription(Id=Ref(ec2Instance), Port="80")
    ],
    UnhealthyThresholdCount="3",
    VpcId=Ref(vpc)
)
template.add_resource(appTargetGroup)

#Creating the listener to match with the target group within our load balancer
#No need to create more listener rules since the only forwarding that our elb will be doing is redirecting to our app.
elbListener = elb.Listener(
    "Listener",
    Port="80",
    Protocol="HTTP",
    LoadBalancerArn=Ref(loadBalancer),
    DefaultActions=[
        elb.Action(Type="forward", TargetGroupArn=Ref(appTargetGroup))
    ]
)
template.add_resource(elbListener)


# Export the CloudFormation script in yaml and json (for testing purposes even though only 1 is required)
with open('troposphere-exercise.yaml','w') as f:
    f.write(template.to_yaml())

with open('troposphere-exercise.json','w') as f:
    f.write(template.to_json())