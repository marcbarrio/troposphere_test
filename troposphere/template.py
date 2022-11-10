#!/usr/bin/python3

from __future__ import print_function

from troposphere import ec2
from troposphere import Tags, Ref, Sub, Export, ImportValue, Base64, GetAtt
from troposphere import Template, Output
from troposphere import elasticloadbalancingv2 as elb
from troposphere import Parameter

###########Comments#############
#All these resources: Subnet, VPC, Ec2 Instance & LoadBalancer are created within the same CloudFormation Stack
#In a real environment those would be created within separate stacks for when we need to change/remove any of them it would not affect to the rest
################################



template = Template()


# Parameter Creation
keyname = Parameter(
    "KeyName",
    Description="Name of an EC2 KeyPair to enable SSH",
    Type="AWS::EC2::KeyPair::KeyName"
)
template.add_parameter(keyname)

#Creation of VPC with CDIR Block 10.0.0.0/24 And a Tag name
vpc = ec2.VPC(
        'VPC',
        CidrBlock="10.0.0.0/16",
        Tags=Tags(
            Name="VPC for troposphere exercise"
        )
    )
template.add_resource(vpc)

#Creation of the internet gateway
internetGateway = ec2.InternetGateway(
    "InternetGateway",
    Tags=Tags(
        Description="Internet gateway attached to VPC"
    )
)
template.add_resource(internetGateway)

gatewayAttachment = ec2.VPCGatewayAttachment(
    "GatewayAttachment",
    VpcId=Ref(vpc),
    InternetGatewayId=Ref(internetGateway)
)
template.add_resource(gatewayAttachment)

routeTable = ec2.RouteTable(
    "RouteTable",
    VpcId=Ref(vpc),
    Tags=Tags(
        Description="Routetable for our VPC"
    )
)
template.add_resource(routeTable)

route = ec2.Route(
    "Route",
    DependsOn="GatewayAttachment",
    GatewayId=Ref(internetGateway),
    DestinationCidrBlock="0.0.0.0/0",
    RouteTableId=Ref(routeTable)
)
template.add_resource(route)

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

# Creating ACL
networkACL = ec2.NetworkAcl(
    "NetworkACL",
    VpcId=Ref(vpc),
    Tags=Tags(
        Description="ACL for VPC"
    )
)
template.add_resource(networkACL)

#Inbound ACL entry for port 80 TCP (HTTP) traffic
inBoundHTTPEntry = ec2.NetworkAclEntry(
    "inboundHTTPentry",
    NetworkAclId=Ref(networkACL),
    RuleNumber="100",
    Protocol="6",
    PortRange=ec2.PortRange(To="80", From="80"),
    Egress="false",
    RuleAction="allow",
    CidrBlock="0.0.0.0/0"
)
template.add_resource(inBoundHTTPEntry)

#Inbound ACL entry for port 22 TCP (SSH) Traffic
inBoundSSHEntry = ec2.NetworkAclEntry(
    "inboundSSHentry",
    NetworkAclId=Ref(networkACL),
    RuleNumber="101",
    Protocol="6",
    PortRange=ec2.PortRange(To="22", From="22"),
    Egress="false",
    RuleAction="allow",
    CidrBlock="0.0.0.0/0"
)
template.add_resource(inBoundSSHEntry)

#Subnet Network ACL Associaton
subnetAclAssociation = ec2.SubnetNetworkAclAssociation(
    "SubnetNetworkAclAssociation",
    SubnetId=Ref(subnet),
    NetworkAclId=Ref(networkACL)
)
template.add_resource(subnetAclAssociation)

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

#Creating security group for the instance in order to be able to access the desired port (80 in this case, can change if exposed port from the docker container changes) from any ip
instancesg = ec2.SecurityGroup(
    "AppSecurityGroup",
    GroupDescription="Enable HTTP access to the instance",
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="80",
            ToPort="80",
            CidrIp="0.0.0.0/0"
        ),
        ec2.SecurityGroupRule(
            IpProtocol="tcp",
            FromPort="22",
            ToPort="22",
            CidrIp="79.152.131.9/32"
        )
    ]
)
template.add_resource(instancesg)

#Creating the EC2 instance to hold our application

ec2Instance = ec2.Instance(
    "ApplicationInstance",
    ImageId="ami-064736ff8301af3ee",
    InstanceType="t2.micro",
    #SubnetId=Ref(subnet),
    Tags=Tags(
        Name="Ec2 instance to hold our application",
        Subnet="Belonging to the subnet 'TestSubnet'"
    ),
    UserData=Base64(userDataDockerInstall),
    #SecurityGroupIds=[GetAtt(instancesg,"GroupId")],
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
            AssociatePublicIpAddress="true",
            DeleteOnTermination="true",
            GroupSet=[Ref(instancesg)],
            SubnetId=Ref(subnet),
            DeviceIndex="0"
        )
    ],
    KeyName=Ref(keyname)
)

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