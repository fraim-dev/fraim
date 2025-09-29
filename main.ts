import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

const allowDb = new aws.ec2.SecurityGroup("allow_db", {
    name: "allow_tls",
    description: "Allow TLS inbound traffic and all outbound traffic",
    vpcId: main.id,
    tags: {
        Name: "allow_tls",
    },
});
const allowDBIpv4 = new aws.vpc.SecurityGroupIngressRule("allow_db_ipv4", {
    securityGroupId: allowDb.id,
    cidrIpv4: "0.0.0.0/0",
    fromPort: 5432,
    ipProtocol: "tcp",
    toPort: 5432,
});
const allowDBIpv6 = new aws.vpc.SecurityGroupIngressRule("allow_db_ipv6", {
    securityGroupId: allowDb.id,
    cidrIpv6: "::/0",
    fromPort: 5432,
    ipProtocol: "tcp",
    toPort: 5432,
});
const allowTrafficIpv4 = new aws.vpc.SecurityGroupEgressRule("allow_traffic_ipv4", {
    securityGroupId: allowDb.id,
    cidrIpv4: "0.0.0.0/0",
    ipProtocol: "-1",
});
const allowTrafficIpv6 = new aws.vpc.SecurityGroupEgressRule("allow_traffic_ipv6", {
    securityGroupId: allowDb.id,
    cidrIpv6: "::/0",
    ipProtocol: "-1",
});
