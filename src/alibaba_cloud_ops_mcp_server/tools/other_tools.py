import logging
from typing import Any
from pydantic import Field

from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
from alibaba_cloud_ops_mcp_server.alibabacloud.utils import create_config
from alibaba_cloud_ops_mcp_server.tools.api_tools import _get_service_endpoint, _tools_api_call


logger = logging.getLogger(__name__)


tools = []





@tools.append
def QueryAccountResources(
        query_input: str = Field(
            description='自然语言查询描述，可以查询资源属性或者数量等信息，例如：查询上海有哪些资源、所有地域的ECS实例数量')
):
    """
    查询账号下的资源信息。
    注意，支持的服务和资源如下所示，当涉及的资源在下列列表中时才需要进行调用
    {"supported_alicloud_resources":[{"service":"容器服务 Kubernetes 版","resources":[{"resource_name":"集群","resource_type":"ACS::ACK::Cluster"}]},{"service":"分布式云容器平台","resources":[{"resource_name":"管控集群","resource_type":"ACS::AckOne::Cluster"}]},{"service":"操作审计","resources":[{"resource_name":"跟踪","resource_type":"ACS::ActionTrail::Trail"}]},{"service":"云原生数据仓库 AnalyticDB MySQL 版","resources":[{"resource_name":"数仓版集群","resource_type":"ACS::ADB::DBCluster"},{"resource_name":"湖仓版集群","resource_type":"ACS::ADB::DBClusterLakeVersion"}]},{"service":"应用型负载均衡 ALB","resources":[{"resource_name":"监听","resource_type":"ACS::ALB::Listener"},{"resource_name":"负载均衡","resource_type":"ACS::ALB::LoadBalancer"},{"resource_name":"服务器组","resource_type":"ACS::ALB::ServerGroup"}]},{"service":"云解析 DNS","resources":[{"resource_name":"全局流量管理实例(新版)","resource_type":"ACS::Alidns::DnsGtmInstance"},{"resource_name":"域名","resource_type":"ACS::Alidns::Domain"},{"resource_name":"全局流量管理实例","resource_type":"ACS::Alidns::GtmInstance"}]},{"service":"消息队列 Kafka 版","resources":[{"resource_name":"消费组","resource_type":"ACS::AliKafka::ConsumerGroup"},{"resource_name":"实例","resource_type":"ACS::AliKafka::Instance"},{"resource_name":"主题","resource_type":"ACS::AliKafka::Topic"}]},{"service":"云原生API网关","resources":[{"resource_name":"网关","resource_type":"ACS::APIG::Gateway"},{"resource_name":"HTTP API接口","resource_type":"ACS::APIG::HttpApi"},{"resource_name":"服务","resource_type":"ACS::APIG::Service"}]},{"service":"API 网关","resources":[{"resource_name":"API","resource_type":"ACS::ApiGateway::Api"},{"resource_name":"应用","resource_type":"ACS::ApiGateway::App"},{"resource_name":"实例","resource_type":"ACS::ApiGateway::Instance"}]},{"service":"应用实时监控服务","resources":[{"resource_name":"Grafana工作区","resource_type":"ACS::ARMS::GrafanaWorkspace"},{"resource_name":"Prometheus实例","resource_type":"ACS::ARMS::Prometheus"},{"resource_name":"应用监控","resource_type":"ACS::ARMS::TraceApp"}]},{"service":"运维安全中心(堡垒机)","resources":[{"resource_name":"实例","resource_type":"ACS::Bastionhost::Instance"}]},{"service":"云速搭","resources":[{"resource_name":"应用","resource_type":"ACS::BPStudio::Application"}]},{"service":"共享带宽","resources":[{"resource_name":"共享带宽实例","resource_type":"ACS::CBWP::CommonBandwidthPackage"}]},{"service":"CDN","resources":[{"resource_name":"域名","resource_type":"ACS::CDN::Domain"}]},{"service":"云企业网","resources":[{"resource_name":"带宽包","resource_type":"ACS::CEN::CenBandwidthPackage"},{"resource_name":"实例","resource_type":"ACS::CEN::CenInstance"},{"resource_name":"流日志","resource_type":"ACS::CEN::Flowlog"},{"resource_name":"转发路由器","resource_type":"ACS::CEN::TransitRouter"},{"resource_name":"边界路由器VBR连接","resource_type":"ACS::CEN::TransitRouterVbrAttachment"},{"resource_name":"专有网络VPC连接","resource_type":"ACS::CEN::TransitRouterVpcAttachment"},{"resource_name":"虚拟专用网VPN连接","resource_type":"ACS::CEN::TransitRouterVpnAttachment"}]},{"service":"云数据库 ClickHouse","resources":[{"resource_name":"社区版集群","resource_type":"ACS::ClickHouse::DBCluster"},{"resource_name":"企业版集群","resource_type":"ACS::ClickHouse::EnterpriseDBCluster"}]},{"service":"云防火墙","resources":[{"resource_name":"实例","resource_type":"ACS::CloudFirewall::Instance"}]},{"service":"云 SSO","resources":[{"resource_name":"用户组","resource_type":"ACS::CloudSSO::Group"}]},{"service":"云存储网关","resources":[{"resource_name":"网关","resource_type":"ACS::CloudStorageGateway::Gateway"}]},{"service":"容器镜像服务","resources":[{"resource_name":"容器镜像实例","resource_type":"ACS::CR::Instance"},{"resource_name":"命名空间","resource_type":"ACS::CR::Namespace"},{"resource_name":"仓库","resource_type":"ACS::CR::Repository"}]},{"service":"数据总线 DataHub","resources":[{"resource_name":"项目","resource_type":"ACS::DataHub::Project"}]},{"service":"DataV数据可视化","resources":[{"resource_name":"工作空间","resource_type":"ACS::DataV::Workspace"}]},{"service":"大数据开发治理平台 DataWorks","resources":[{"resource_name":"Dataworks资源组","resource_type":"ACS::DataWorks::DwResourceGroup"},{"resource_name":"工作空间","resource_type":"ACS::DataWorks::Project"}]},{"service":"数据库备份","resources":[{"resource_name":"备份计划","resource_type":"ACS::DBS::BackupPlan"}]},{"service":"全站加速DCDN","resources":[{"resource_name":"全站加速域名","resource_type":"ACS::DCDN::Domain"},{"resource_name":"IPA域名","resource_type":"ACS::DCDN::IpaDomain"}]},{"service":"DDoS 原生防护","resources":[{"resource_name":"实例","resource_type":"ACS::DdosBgp::Instance"}]},{"service":"DDoS 高防","resources":[{"resource_name":"实例","resource_type":"ACS::DdosCoo::Instance"}]},{"service":"域名","resources":[{"resource_name":"域名","resource_type":"ACS::Domain::Domain"}]},{"service":"云原生分布式数据库 PolarDB-X","resources":[{"resource_name":"PolarDB-X 1.0 实例","resource_type":"ACS::DRDS::DBInstance"},{"resource_name":"PolarDB-X 2.0 实例","resource_type":"ACS::DRDS::PolarDBXInstance"}]},{"service":"数据传输","resources":[{"resource_name":"实例","resource_type":"ACS::DTS::Instance"}]},{"service":"弹性加速计算实例","resources":[{"resource_name":"实例","resource_type":"ACS::EAIS::Instance"}]},{"service":"块存储","resources":[{"resource_name":"专属集群","resource_type":"ACS::EBS::DedicatedBlockStorageCluster"},{"resource_name":"一致性复制组","resource_type":"ACS::EBS::DiskReplicaGroup"},{"resource_name":"云盘复制对","resource_type":"ACS::EBS::DiskReplicaPair"}]},{"service":"弹性容器实例","resources":[{"resource_name":"容器组","resource_type":"ACS::ECI::ContainerGroup"},{"resource_name":"镜像缓存","resource_type":"ACS::ECI::ImageCache"}]},{"service":"弹性云手机","resources":[{"resource_name":"实例","resource_type":"ACS::ECP::Instance"}]},{"service":"云服务器 ECS","resources":[{"resource_name":"自动快照策略","resource_type":"ACS::ECS::AutoSnapshotPolicy"},{"resource_name":"容量预定","resource_type":"ACS::ECS::CapacityReservation"},{"resource_name":"专用宿主机","resource_type":"ACS::ECS::DedicatedHost"},{"resource_name":"磁盘","resource_type":"ACS::ECS::Disk"},{"resource_name":"弹性保障服务","resource_type":"ACS::ECS::ElasticityAssurance"},{"resource_name":"镜像","resource_type":"ACS::ECS::Image"},{"resource_name":"实例","resource_type":"ACS::ECS::Instance"},{"resource_name":"密钥对","resource_type":"ACS::ECS::KeyPair"},{"resource_name":"弹性网卡","resource_type":"ACS::ECS::NetworkInterface"},{"resource_name":"安全组","resource_type":"ACS::ECS::SecurityGroup"},{"resource_name":"快照","resource_type":"ACS::ECS::Snapshot"}]},{"service":"智能计算灵骏","resources":[{"resource_name":"集群","resource_type":"ACS::Eflo::Cluster"},{"resource_name":"节点","resource_type":"ACS::Eflo::Node"}]},{"service":"弹性高性能计算","resources":[{"resource_name":"集群","resource_type":"ACS::Ehpc::Cluster"}]},{"service":"弹性公网 IP","resources":[{"resource_name":"弹性公网 IP","resource_type":"ACS::EIP::EipAddress"}]},{"service":"任播弹性公网 IP","resources":[{"resource_name":"AnycastEip 地址","resource_type":"ACS::Eipanycast::AnycastEipAddress"}]},{"service":"检索分析服务 Elasticsearch版","resources":[{"resource_name":"Elasticsearch实例","resource_type":"ACS::Elasticsearch::Instance"},{"resource_name":"Logstash实例","resource_type":"ACS::Elasticsearch::Logstash"}]},{"service":"EMR Serverless Spark","resources":[{"resource_name":"工作空间","resource_type":"ACS::EmrServerlessSpark::Workspace"}]},{"service":"边缘节点服务ENS","resources":[{"resource_name":"实例","resource_type":"ACS::ENS::Instance"}]},{"service":"边缘安全加速ESA","resources":[{"resource_name":"站点","resource_type":"ACS::ESA::Site"}]},{"service":"弹性伸缩","resources":[{"resource_name":"伸缩组","resource_type":"ACS::ESS::ScalingGroup"}]},{"service":"高速通道","resources":[{"resource_name":"物理专线","resource_type":"ACS::ExpressConnect::PhysicalConnection"},{"resource_name":"边界路由器VBR实例","resource_type":"ACS::ExpressConnect::VirtualBorderRouter"}]},{"service":"高速通道专线网关","resources":[{"resource_name":"专线网关","resource_type":"ACS::ExpressConnectRouter::ExpressConnectRouter"}]},{"service":"全球加速","resources":[{"resource_name":"加速","resource_type":"ACS::Ga::Accelerator"},{"resource_name":"带宽包","resource_type":"ACS::Ga::BandwidthPackage"}]},{"service":"云原生数据仓库 AnalyticDB PostgreSQL版","resources":[{"resource_name":"实例","resource_type":"ACS::GPDB::DBInstance"}]},{"service":"图数据库","resources":[{"resource_name":"实例","resource_type":"ACS::GraphDatabase::DbInstance"}]},{"service":"云数据库 HBase 版","resources":[{"resource_name":"集群","resource_type":"ACS::HBase::Cluster"}]},{"service":"云备份","resources":[{"resource_name":"SAP HANA 实例","resource_type":"ACS::HBR::HanaInstance"},{"resource_name":"存储库","resource_type":"ACS::HBR::Vault"}]},{"service":"实时数仓Hologres","resources":[{"resource_name":"实例","resource_type":"ACS::Hologram::Instance"}]},{"service":"密钥管理服务","resources":[{"resource_name":"主密钥","resource_type":"ACS::KMS::Key"}]},{"service":"云原生多模数据库 Lindorm","resources":[{"resource_name":"实例","resource_type":"ACS::Lindorm::Instance"}]},{"service":"视频直播","resources":[{"resource_name":"域名","resource_type":"ACS::Live::Domain"}]},{"service":"云原生大数据计算服务 MaxCompute","resources":[{"resource_name":"项目","resource_type":"ACS::MaxCompute::Project"}]},{"service":"消息服务 MNS","resources":[{"resource_name":"队列","resource_type":"ACS::MessageService::Queue"},{"resource_name":"主题","resource_type":"ACS::MessageService::Topic"}]},{"service":"云数据库 MongoDB 版","resources":[{"resource_name":"实例","resource_type":"ACS::MongoDB::DBInstance"}]},{"service":"微服务引擎","resources":[{"resource_name":"集群","resource_type":"ACS::MSE::Cluster"},{"resource_name":"云原生网关","resource_type":"ACS::MSE::Gateway"}]},{"service":"文件存储 NAS","resources":[{"resource_name":"文件系统","resource_type":"ACS::NAS::FileSystem"}]},{"service":"NAT 网关","resources":[{"resource_name":"NAT网关","resource_type":"ACS::NAT::NatGateway"}]},{"service":"网络型负载均衡","resources":[{"resource_name":"监听","resource_type":"ACS::NLB::Listener"},{"resource_name":"负载均衡","resource_type":"ACS::NLB::LoadBalancer"},{"resource_name":"服务器组","resource_type":"ACS::NLB::ServerGroup"}]},{"service":"云数据库 OceanBase 版","resources":[{"resource_name":"实例","resource_type":"ACS::OceanBase::Instance"}]},{"service":"消息队列 RocketMQ 4.0 版","resources":[{"resource_name":"消费组","resource_type":"ACS::Ons::Group"},{"resource_name":"实例","resource_type":"ACS::Ons::Instance"},{"resource_name":"主题","resource_type":"ACS::Ons::Topic"}]},{"service":"系统运维管理","resources":[{"resource_name":"应用","resource_type":"ACS::OOS::Application"}]},{"service":"智能开放搜索 OpenSearch","resources":[{"resource_name":"应用","resource_type":"ACS::OpenSearch::AppGroup"}]},{"service":"对象存储 OSS","resources":[{"resource_name":"Bucket","resource_type":"ACS::OSS::Bucket"}]},{"service":"表格存储","resources":[{"resource_name":"实例","resource_type":"ACS::OTS::Instance"}]},{"service":"人工智能平台 PAI","resources":[{"resource_name":"服务","resource_type":"ACS::PAI::Service"}]},{"service":"云原生数据库 PolarDB","resources":[{"resource_name":"集群","resource_type":"ACS::PolarDB::DBCluster"}]},{"service":"私网连接","resources":[{"resource_name":"终端节点","resource_type":"ACS::PrivateLink::VpcEndpoint"},{"resource_name":"终端节点服务","resource_type":"ACS::PrivateLink::VpcEndpointService"}]},{"service":"云解析 PrivateZone","resources":[{"resource_name":"私有域","resource_type":"ACS::PrivateZone::Zone"}]},{"service":"访问控制","resources":[{"resource_name":"用户组","resource_type":"ACS::RAM::Group"},{"resource_name":"权限策略","resource_type":"ACS::RAM::Policy"},{"resource_name":"角色","resource_type":"ACS::RAM::Role"},{"resource_name":"用户","resource_type":"ACS::RAM::User"}]},{"service":"云数据库 RDS","resources":[{"resource_name":"实例","resource_type":"ACS::RDS::DBInstance"}]},{"service":"实时计算 Flink版","resources":[{"resource_name":"实例","resource_type":"ACS::RealtimeCompute::VvpInstance"}]},{"service":"云数据库 Tair(兼容 Redis)","resources":[{"resource_name":"实例","resource_type":"ACS::Redis::DBInstance"}]},{"service":"资源管理","resources":[{"resource_name":"成员账号","resource_type":"ACS::ResourceManager::Account"},{"resource_name":"资源夹","resource_type":"ACS::ResourceManager::Folder"},{"resource_name":"资源目录","resource_type":"ACS::ResourceManager::ResourceDirectory"}]},{"service":"消息队列 RocketMQ 5.0 版","resources":[{"resource_name":"消费者分组","resource_type":"ACS::RocketMQ::ConsumerGroup"},{"resource_name":"实例","resource_type":"ACS::RocketMQ::Instance"},{"resource_name":"主题","resource_type":"ACS::RocketMQ::Topic"}]},{"service":"资源编排","resources":[{"resource_name":"资源栈","resource_type":"ACS::ROS::Stack"},{"resource_name":"资源栈组","resource_type":"ACS::ROS::StackGroup"}]},{"service":"音视频通信RTC","resources":[{"resource_name":"应用","resource_type":"ACS::RTC::Application"}]},{"service":"安全加速 SCDN","resources":[{"resource_name":"域名","resource_type":"ACS::SCDN::Domain"}]},{"service":"数据安全中心","resources":[{"resource_name":"实例","resource_type":"ACS::SDDP::Instance"}]},{"service":"云数据库 SelectDB 版","resources":[{"resource_name":"实例","resource_type":"ACS::SelectDB::DBInstance"}]},{"service":"传统型负载均衡 CLB (原SLB)","resources":[{"resource_name":"访问控制列表","resource_type":"ACS::SLB::AccessControlList"},{"resource_name":"CA证书","resource_type":"ACS::SLB::CACertificate"},{"resource_name":"实例","resource_type":"ACS::SLB::LoadBalancer"},{"resource_name":"服务器证书","resource_type":"ACS::SLB::ServerCertificate"},{"resource_name":"虚拟服务器组","resource_type":"ACS::SLB::VServerGroup"}]},{"service":"日志服务","resources":[{"resource_name":"日志库","resource_type":"ACS::SLS::LogStore"},{"resource_name":"日志项目","resource_type":"ACS::SLS::Project"}]},{"service":"短信服务","resources":[{"resource_name":"模板","resource_type":"ACS::SMS::Template"}]},{"service":"数字证书管理服务","resources":[{"resource_name":"SSL证书","resource_type":"ACS::SSLCertificatesService::Certificate"}]},{"service":"轻量应用服务器","resources":[{"resource_name":"实例","resource_type":"ACS::SWAS::Instance"}]},{"service":"云安全中心","resources":[{"resource_name":"实例","resource_type":"ACS::ThreatDetection::Instance"}]},{"service":"时间序列数据库","resources":[{"resource_name":"实例","resource_type":"ACS::TSDB::Instance"}]},{"service":"视频点播","resources":[{"resource_name":"域名","resource_type":"ACS::VOD::Domain"}]},{"service":"专有网络 VPC","resources":[{"resource_name":"IPv4网关","resource_type":"ACS::VPC::Ipv4Gateway"},{"resource_name":"IPv6地址","resource_type":"ACS::VPC::Ipv6Address"},{"resource_name":"IPv6网关","resource_type":"ACS::VPC::Ipv6Gateway"},{"resource_name":"网络ACL","resource_type":"ACS::VPC::NetworkAcl"},{"resource_name":"VPC对等连接","resource_type":"ACS::VPC::PeerConnection"},{"resource_name":"路由表","resource_type":"ACS::VPC::RouteTable"},{"resource_name":"专有网络","resource_type":"ACS::VPC::VPC"},{"resource_name":"交换机","resource_type":"ACS::VPC::VSwitch"}]},{"service":"VPN 网关","resources":[{"resource_name":"用户网关","resource_type":"ACS::VPN::CustomerGateway"},{"resource_name":"IPsec服务端","resource_type":"ACS::VPN::IpsecServer"},{"resource_name":"SSL-VPN 客户端证书","resource_type":"ACS::VPN::SslVpnClientCert"},{"resource_name":"SSL-VPN 服务端","resource_type":"ACS::VPN::SslVpnServer"},{"resource_name":"IPsec连接","resource_type":"ACS::VPN::VpnConnection"},{"resource_name":"VPN 网关","resource_type":"ACS::VPN::VpnGateway"}]},{"service":"Web应用防火墙3.0","resources":[{"resource_name":"防护对象","resource_type":"ACS::WAFV3::DefenseResource"}]}]}
    Args:
        query_input (str):
            自然语言查询描述，可以查询资源属性或者数量等信息，例如："查询上海有哪些资源"、"查询东南亚地区的 ECS 实例"、"所有地域的ECS实例数量"等。

    Returns:
        ToolResponse:
            返回资源查询结果（JSON 文本）。
    """
    try:
        # 第一步：调用 GenerateSQLQueryByAI 生成 SQL
        service = 'resourcecenter'

        # 创建客户端和参数
        config = create_config()
        config.endpoint = _get_service_endpoint(service, 'cn-hangzhou')
        client = OpenApiClient(config)

        # 调用 GenerateSQLQueryByAI
        queries_generate = {'Input': query_input}
        params_generate = open_api_models.Params(
            action='GenerateSQLQueryByAI',
            version='2022-12-01',
            protocol='HTTPS',
            method='POST',
            auth_type='AK',
            style='RPC',
            pathname='/',
            req_body_type='json',
            body_type='json'
        )
        request_generate = open_api_models.OpenApiRequest(
            query=OpenApiUtilClient.query(queries_generate)
        )
        runtime = util_models.RuntimeOptions()

        logger.info(f'Call GenerateSQLQueryByAI: Input={query_input}')
        resp_generate = client.call_api(params_generate, request_generate, runtime)
        logger.info(f'GenerateSQLQueryByAI Response: {resp_generate}')

        # 从响应中提取 SQL
        body = resp_generate.get('body', {})
        sql = body.get('Sql', '')

        if not sql:
            error_msg = f"生成 SQL 失败，响应: {resp_generate}"
            logger.error(error_msg)
            return error_msg

        logger.info(f'Generated SQL: {sql}')

        # 第二步：调用 ExecuteSQLQuery 执行 SQL 查询
        queries_execute = {'Expression': sql}
        params_execute = open_api_models.Params(
            action='ExecuteSQLQuery',
            version='2022-12-01',
            protocol='HTTPS',
            method='POST',
            auth_type='AK',
            style='RPC',
            pathname='/',
            req_body_type='json',
            body_type='json'
        )
        request_execute = open_api_models.OpenApiRequest(
            query=OpenApiUtilClient.query(queries_execute)
        )

        logger.info(f'Call ExecuteSQLQuery: Expression={sql}')
        resp_execute = client.call_api(params_execute, request_execute, runtime)
        logger.info(f'ExecuteSQLQuery Response: {resp_execute}')

        # 返回查询结果
        return resp_execute

    except Exception as e:
        error_msg = f"查询资源失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@tools.append
def DescribeZones(
        region_id: str = Field(description='地域ID,例如:cn-hangzhou、cn-beijing、cn-shanghai等')
):
    """查询指定地域下的可用区列表

    Args:
        region_id (`str`):
            地域ID,例如:cn-hangzhou(杭州)、cn-beijing(北京)、cn-shanghai(上海)等

    Returns:
        `ToolResponse`:
            返回指定地域下的可用区列表,包括可用区ID
    """
    try:
        # 调用 ECS DescribeZones API 查询可用区信息
        parameters = {
            'RegionId': region_id
        }
        resp = _tools_api_call('ecs', 'DescribeZones', parameters, ctx=None)

        # 解析返回结果,提取可用区ID列表
        zones = resp.get('body', {}).get('Zones', {}).get('Zone', [])

        if not zones:
            text = f"地域 {region_id} 下未查询到可用区信息,可能是不支持的地域ID或API调用失败"
        else:
            # 提取可用区ID列表
            zone_ids = [zone.get('ZoneId') for zone in zones if zone.get('ZoneId')]

            # 格式化输出为纯文本列表
            text = f"地域 {region_id} 的可用区列表:\n"
            for idx, zone_id in enumerate(zone_ids, 1):
                text += f"{idx}. {zone_id}\n"
            text += f"共 {len(zone_ids)} 个可用区"

        return text
    except Exception as e:
        error_text = f"查询地域 {region_id} 的可用区时发生错误: {str(e)}"
        logger.error(error_text, exc_info=True)
        return error_text
