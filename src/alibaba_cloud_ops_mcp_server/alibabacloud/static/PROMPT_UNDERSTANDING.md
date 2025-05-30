## Optimized Prompt

After the user submits a request, please first analyze which direction the user's needs correspond to, and check whether there are corresponding tools available in the feature list. If yes, directly use the relevant tool to fulfill the request. If not, proceed to the **retrieval phase** described below.

---

### Retrieval Phase (Please execute the following steps sequentially)

1. **Determine the desired Alibaba Cloud service**

   The following Alibaba Cloud services are supported by this MCP Server. Please select the most suitable one based on the user's request.  
   If no matching service is found, please respond with: `Unfortunately, we currently do not support this service`

   Supported Services:
   - ecs: Elastic Compute Service (ECS)
   - oos: Operations Orchestration Service (OOS)
   - rds: Relational Database Service (RDS)
   - oss: Object Storage Service (OSS)
   - vpc: Virtual Private Cloud (VPC)
   - slb: Server Load Balancer (SLB)
   - ess: Elastic Scaling (ESS)
   - ros: Resource Orchestration Service (ROS)
   - cbn: Cloud Enterprise Network(CBN)
   - dds: MongoDB Database Service (DDS)
   - r-kvstore: Cloud database Tair (compatible with Redis) (R-KVStore)

2. **Identify the corresponding API**

   Use the tool: `ListAPIs`, to list all available APIs for the selected service.

3. **Obtain the required parameters for calling the API**

   Use the tool: `GetAPIInfo`, to retrieve detailed information and required parameters for the API.

4. **Call the API to perform the actual operation**

   Use the tool: `CommonAPICaller` to execute the API call.

---

### Notes

- For each tool’s output, please filter out only the most appropriate single result.
- Based on your reasoning, choose the best-suited service and API, and complete the call accordingly.
- If multiple candidate results exist, make your decision based on the user's request, context, semantics, and common usage scenarios.

---

## Feature List (Tool)

| Product | Tool | Function | Implementation Method | Status |
| --- | --- | --- | --- | --- |
| ECS | RunCommand | Run Command | OOS | Done |
|  | StartInstances | Start Instance | OOS | Done |
|  | StopInstances | Stop Instance | OOS | Done |
|  | RebootInstances | Reboot Instance | OOS | Done |
|  | DescribeInstances | View Instances | API | Done |
|  | DescribeRegions | View Regions | API | Done |
|  | DescribeZones | View Zones | API | Done |
|  | DescribeAvailableResource | View Resource Inventory | API | Done |
|  | DescribeImages | View Images | API | Done |
|  | DescribeSecurityGroups | View Security Groups | API | Done |
|  | RunInstances | Create Instance | OOS | Done |
|  | DeleteInstances | Delete Instance | API | Done |
|  | ResetPassword | Change Password | OOS | Done |
|  | ReplaceSystemDisk | Change Operating System | OOS | Done |
| VPC | DescribeVpcs | View VPCs | API | Done |
|  | DescribeVSwitches | View VSwitches | API | Done |
| RDS | DescribeDBInstances | Query Database Instances | API | Done |
|  | StartDBInstances | Start RDS Instances | OOS | Done |
|  | StopDBInstances | Stop RDS Instances | OOS | Done |
|  | RestartDBInstances | Restart RDS Instances | OOS | Done |
| OSS | ListBuckets | View Buckets | API | Done |
|  | PutBucket | Create Bucket | API | Done |
|  | DeleteBucket | Delete Bucket | API | Done |
|  | ListObjects | View Files in Bucket | API | Done |
| CloudMonitor | GetCpuUsageData | Get CPU Usage of ECS Instances | API | Done |
|  | GetCpuLoadavgData | Get CPU 1-minute Average Load | API | Done |
|  | GetCpuloadavg5mData | Get CPU 5-minute Average Load | API | Done |
|  | GetCpuloadavg15mData | Get CPU 15-minute Average Load | API | Done |
|  | GetMemUsedData | Get Memory Usage | API | Done |
|  | GetMemUsageData | Get Memory Utilization | API | Done |
|  | GetDiskUsageData | Get Disk Utilization | API | Done |
|  | GetDiskTotalData | Get Total Disk Capacity | API | Done |
|  | GetDiskUsedData | Get Disk Usage | API | Done |

---
