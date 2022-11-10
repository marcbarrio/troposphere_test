#!/usr/bin/python3

from __future__ import print_function

from troposphere import ec2
from troposphere import Tags, Ref, Sub, Export, ImportValue, Base64, GetAtt, Join
from troposphere import Template, Output
from troposphere import elasticloadbalancingv2 as elb
from troposphere import Parameter

###########Comments#############
#All these resources: Subnet, VPC, Ec2 Instance & LoadBalancer are created within the same CloudFormation Stack
#In a real environment those would be created within separate stacks for when we need to change/remove any of them it would not affect to the rest
################################



template = Template()


# Parameter Creation
keyname = template.add_parameter(
    Parameter(
    "KeyName",
    Description="Name of an EC2 KeyPair to enable SSH",
    Type="AWS::EC2::KeyPair::KeyName"
    )
)

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

#Creation of the internet gateway
internetGateway = template.add_resource(
    ec2.InternetGateway(
        "InternetGateway",
        Tags=Tags(
            Description="Internet gateway attached to VPC"
        )
    )
)

gatewayAttachment = template.add_resource(
    ec2.VPCGatewayAttachment(
        "GatewayAttachment",
        VpcId=Ref(vpc),
        InternetGatewayId=Ref(internetGateway)
    )
)

routeTable = template.add_resource(
    ec2.RouteTable(
        "RouteTable",
        VpcId=Ref(vpc),
        Tags=Tags(
           Description="Routetable for our VPC"
        )
    )
)

route = template.add_resource(
    ec2.Route(
        "Route",
        DependsOn="GatewayAttachment",
        GatewayId=Ref(internetGateway),
        DestinationCidrBlock="0.0.0.0/0",
        RouteTableId=Ref(routeTable)
    )
)


#Creation of Subnet with same CidrBlock as VPC and the VPC id from the previously created.
subnet = template.add_resource(
    ec2.Subnet(
        "TestSubnet",
        AvailabilityZone="eu-west-3c",
        CidrBlock="10.0.0.0/24",
        VpcId=Ref(vpc),
        Tags=Tags(
            Name="Subnet for troposphere exercise",
            ZoneBlock="eu-west-3c (Paris) & 10.0.0.0/24"
        )
    )
)

#Associating the routetable with subnet
subnetRouteTableAssociation = template.add_resource(
    ec2.SubnetRouteTableAssociation(
        "SubnetRouteTableAssociation",
        SubnetId=Ref(subnet),
        RouteTableId=Ref(routeTable)
    )
)

#Creating an output value to the subnet for hypothetical future use on other stacks
output_subnet = Output("outputSubnet")
output_subnet.Value = Ref(subnet)
output_subnet.Export = Export(Sub("${AWS::StackName}-" + subnet.title))

template.add_output(output_subnet)

#Creating a 2nd Subnet for the minimum required in the ELB
subnet2 = template.add_resource(
    ec2.Subnet(
        "TestSubnet2",
        AvailabilityZone="eu-west-3a",
        CidrBlock="10.0.1.0/24",
        VpcId=Ref(vpc),
        Tags=Tags(
            Name="Subnet for ELB required input",
            ZoneBlock="eu-west-3a (Paris) & 10.0.1.0/24"
        )
    )
)

# Creating ACL
networkACL = template.add_resource(
    ec2.NetworkAcl(
        "NetworkACL",
        VpcId=Ref(vpc),
        Tags=Tags(
            Description="ACL for VPC"
        )
    )
)

#Inbound ACL entry for port 80 TCP (HTTP) traffic
inBoundHTTPEntry = template.add_resource(
    ec2.NetworkAclEntry(
        "inboundHTTPentry",
        NetworkAclId=Ref(networkACL),
        RuleNumber="100",
        Protocol="6",
        PortRange=ec2.PortRange(To="80", From="80"),
        Egress="false",
        RuleAction="allow",
        CidrBlock="0.0.0.0/0"
    )
)

#Inbound ACL entry for port 22 TCP (SSH) Traffic
inBoundSSHEntry = template.add_resource(
    ec2.NetworkAclEntry(
        "inboundSSHentry",
        NetworkAclId=Ref(networkACL),
        RuleNumber="101",
        Protocol="6",
        PortRange=ec2.PortRange(To="22", From="22"),
        Egress="false",
        RuleAction="allow",
        CidrBlock="0.0.0.0/0"
    )
)

#InboundEphemeralPorts to allow updates and installs on ubuntu. This is not a very secure approach if we want to use ACLs as a main security tool besides security groups
#A script could be created when in need for those ephemeral ports which would, via aws cli, create and enable this acl entry and delete it once there is no longer use for those
inBoundEphemeralEntry = template.add_resource(
    ec2.NetworkAclEntry(
        "inBoundEphemeralEntry",
        NetworkAclId=Ref(networkACL),
        RuleNumber="102",
        Protocol="6",
        PortRange=ec2.PortRange(To="65535", From="1024"),
        Egress="false",
        RuleAction="allow",
        CidrBlock="0.0.0.0/0"
    )
)

#OutBound ACL entry for HTTP Traffic
outBoundHttpEntry = template.add_resource(
    ec2.NetworkAclEntry(
        "outBoundHttpEntry",
        NetworkAclId=Ref(networkACL),
        RuleNumber="100",
        Protocol="6",
        PortRange=ec2.PortRange(To="80", From="80"),
        Egress="true",
        RuleAction="allow",
        CidrBlock="0.0.0.0/0"
    )
)

#OutBound ACL entry for HTTPS Traffic
outBoundHttpsEntry = template.add_resource(
    ec2.NetworkAclEntry(
        "outBoundHttpsEntry",
        NetworkAclId=Ref(networkACL),
        RuleNumber="101",
        Protocol="6",
        PortRange=ec2.PortRange(To="443", From="443"),
        Egress="true",
        RuleAction="allow",
        CidrBlock="0.0.0.0/0"
    )
)

#Outbound ACL entry for ephemeral ports 1024-65545 for SSH response
outBoundResponseEntry = template.add_resource(
    ec2.NetworkAclEntry(
        "outBoundResponseEntry",
        NetworkAclId=Ref(networkACL),
        RuleNumber="102",
        Protocol="6",
        PortRange=ec2.PortRange(To="65535", From="1024"),
        Egress="true",
        RuleAction="allow",
        CidrBlock="0.0.0.0/0"
    )
)


#Subnet Network ACL Associaton
subnetAclAssociation = template.add_resource(
    ec2.SubnetNetworkAclAssociation(
        "SubnetNetworkAclAssociation",
        SubnetId=Ref(subnet),
        NetworkAclId=Ref(networkACL)
    )
)

userDataDockerInstall = [
    "#!/bin/bash -xe\n",
    "sudo apt-get update\n",
    "sudo apt-get install -y ca-certificates curl gnupg lsb-release\n",
    "sudo mkdir -p /etc/apt/keyrings\n",
    "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg\n",
    """echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null\n""",
    "sudo apt-get update\n",
    "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin\n",
    "sudo usermod -aG docker ubuntu\n"
]

#Creating security group for the instance in order to be able to access the desired port (80 in this case, can change if exposed port from the docker container changes) from any ip
instancesg = template.add_resource(
    ec2.SecurityGroup(
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
)

#Creating the EC2 instance to hold our application

ec2Instance = template.add_resource(
    ec2.Instance(
        "ApplicationInstance",
        ImageId="ami-064736ff8301af3ee",
        InstanceType="t2.micro",
        Tags=Tags(
            Name="Ec2 instance to hold our application",
            Subnet="Belonging to the subnet 'TestSubnet'"
        ),
        UserData=Base64(Join("",userDataDockerInstall)),
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
)

#Creating the security group for the loadbalancer
elbSecurityGroup = template.add_resource(
    ec2.SecurityGroup(
        "ELBSecurityGroup",
        GroupDescription="Security Group used by the Load Balancer",
        VpcId=Ref(vpc),
        SecurityGroupIngress=[
            ec2.SecurityGroupRule(
                IpProtocol="tcp",
                FromPort="80",
                ToPort="80",
                CidrIp="0.0.0.0/0"
            )
        ]
    )
)

#Creating the loadbalancer 
loadBalancer = template.add_resource(
    elb.LoadBalancer(
        "ApplicationLoadBalancer",
        Name="ApplicationELB",
        Scheme="internet-facing",
        Subnets=[Ref(subnet),Ref(subnet2)],
        SecurityGroups=[GetAtt(elbSecurityGroup,"GroupId")],
        Tags=Tags(
            Name="ApplicationELB"
        )
    )
)

#Creating the target group for our application
appTargetGroup = template.add_resource(
    elb.TargetGroup(
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
)

#Creating the listener to match with the target group within our load balancer
#No need to create more listener rules since the only forwarding that our elb will be doing is redirecting to our app.
elbListener = template.add_resource(
    elb.Listener(
        "Listener",
        Port="80",
        Protocol="HTTP",
        LoadBalancerArn=Ref(loadBalancer),
        DefaultActions=[
            elb.Action(Type="forward", TargetGroupArn=Ref(appTargetGroup))
        ]
    )
)


# Export the CloudFormation script in yaml and json (for testing purposes even though only 1 is required)
with open('troposphere-exercise.yaml','w') as f:
    f.write(template.to_yaml())

with open('troposphere-exercise.json','w') as f:
    f.write(template.to_json())