# LurkBot 部署指南

本文档介绍如何使用 Docker 和 Kubernetes 部署 LurkBot。

## 目录

- [Docker 部署](#docker-部署)
  - [快速开始](#快速开始)
  - [构建镜像](#构建镜像)
  - [运行服务](#运行服务)
  - [配置说明](#配置说明)
- [Kubernetes 部署](#kubernetes-部署)
  - [前置条件](#前置条件)
  - [部署步骤](#部署步骤)
  - [配置管理](#配置管理)
  - [扩缩容](#扩缩容)
- [生产环境建议](#生产环境建议)

---

## Docker 部署

### 快速开始

```bash
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env 文件，填入 API 密钥
vim .env

# 3. 启动服务
docker compose up -d

# 4. 查看日志
docker compose logs -f

# 5. 检查健康状态
curl http://localhost:18789/health
```

### 构建镜像

LurkBot 提供多个构建目标：

| 目标 | 描述 | 用途 |
|------|------|------|
| `runtime` | 生产镜像 | 默认部署 |
| `development` | 开发镜像 | 本地开发 |
| `browser` | 浏览器镜像 | 需要 Playwright |

```bash
# 构建生产镜像
docker build -t lurkbot:latest --target runtime .

# 构建开发镜像
docker build -t lurkbot:dev --target development .

# 构建浏览器镜像
docker build -t lurkbot:browser --target browser .
```

### 运行服务

#### Gateway 服务（默认）

```bash
# 启动 gateway
docker compose up -d gateway

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f gateway
```

#### CLI 服务

```bash
# 运行 CLI 命令
docker compose --profile cli run cli --help

# 交互式聊天
docker compose --profile cli run cli chat

# 配置向导
docker compose --profile cli run cli wizard
```

#### 开发模式

```bash
# 启动开发服务（带热重载）
docker compose --profile dev up dev
```

#### 浏览器自动化

```bash
# 启动浏览器服务
docker compose --profile browser up browser
```

### 配置说明

#### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `LURKBOT_GATEWAY_HOST` | 绑定地址 | `0.0.0.0` |
| `LURKBOT_GATEWAY_PORT` | 端口 | `18789` |
| `LURKBOT_ANTHROPIC_API_KEY` | Anthropic API 密钥 | - |
| `LURKBOT_OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `LURKBOT_LOG_LEVEL` | 日志级别 | `INFO` |

完整环境变量列表请参考 `.env.example`。

#### 卷挂载

| 路径 | 描述 |
|------|------|
| `/home/lurkbot/.lurkbot` | 配置目录 |
| `/home/lurkbot/workspace` | 工作空间 |

```bash
# 使用自定义配置目录
LURKBOT_CONFIG_DIR=/path/to/config docker compose up -d
```

---

## Kubernetes 部署

### 前置条件

- Kubernetes 1.25+
- kubectl 配置完成
- 可选：Helm 3.x
- 可选：cert-manager（用于 TLS）

### 部署步骤

#### 1. 创建命名空间

```bash
kubectl apply -f k8s/namespace.yaml
```

#### 2. 配置 Secrets

```bash
# 复制模板
cp k8s/secret.yaml.template k8s/secret.yaml

# 编辑并填入 base64 编码的密钥
# echo -n "your-api-key" | base64
vim k8s/secret.yaml

# 应用 secrets
kubectl apply -f k8s/secret.yaml
```

#### 3. 部署应用

```bash
# 使用 kustomize 部署所有资源
kubectl apply -k k8s/

# 或者逐个部署
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml
kubectl apply -f k8s/ingress.yaml
```

#### 4. 验证部署

```bash
# 查看 Pod 状态
kubectl get pods -n lurkbot

# 查看服务
kubectl get svc -n lurkbot

# 查看日志
kubectl logs -f -l app.kubernetes.io/name=lurkbot -n lurkbot

# 端口转发测试
kubectl port-forward svc/lurkbot-gateway 18789:18789 -n lurkbot

# 健康检查
curl http://localhost:18789/health
```

### 配置管理

#### ConfigMap

非敏感配置存储在 ConfigMap 中：

```bash
# 查看当前配置
kubectl get configmap lurkbot-config -n lurkbot -o yaml

# 更新配置
kubectl edit configmap lurkbot-config -n lurkbot

# 重启 Pod 以应用新配置
kubectl rollout restart deployment/lurkbot-gateway -n lurkbot
```

#### Secrets

敏感配置存储在 Secrets 中：

```bash
# 更新 secret
kubectl create secret generic lurkbot-secrets \
  --from-literal=LURKBOT_ANTHROPIC_API_KEY=sk-ant-... \
  --dry-run=client -o yaml | kubectl apply -f -

# 或使用 External Secrets Operator
```

### 扩缩容

#### 手动扩缩容

```bash
# 扩展到 5 个副本
kubectl scale deployment/lurkbot-gateway --replicas=5 -n lurkbot
```

#### 自动扩缩容 (HPA)

HPA 已配置，基于 CPU 和内存使用率自动扩缩容：

```bash
# 查看 HPA 状态
kubectl get hpa -n lurkbot

# 查看详细信息
kubectl describe hpa lurkbot-gateway-hpa -n lurkbot
```

HPA 配置：
- 最小副本数：2
- 最大副本数：10
- CPU 目标使用率：70%
- 内存目标使用率：80%

---

## 生产环境建议

### 安全性

1. **使用 TLS**
   ```yaml
   # 在 ingress.yaml 中启用 TLS
   tls:
     - hosts:
         - lurkbot.example.com
       secretName: lurkbot-tls
   ```

2. **网络策略**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: lurkbot-network-policy
     namespace: lurkbot
   spec:
     podSelector:
       matchLabels:
         app.kubernetes.io/name: lurkbot
     policyTypes:
       - Ingress
       - Egress
     ingress:
       - from:
           - namespaceSelector:
               matchLabels:
                 name: ingress-nginx
         ports:
           - port: 18789
   ```

3. **使用 External Secrets**
   - 推荐使用 External Secrets Operator 或 Vault 管理敏感配置

### 可观测性

1. **日志收集**
   - 配置 Fluentd/Fluent Bit 收集日志
   - 日志格式已设置为 JSON

2. **指标监控**
   - Prometheus 注解已配置
   - 可通过 `/metrics` 端点获取指标

3. **链路追踪**
   - 支持 OpenTelemetry
   - 配置 `JAEGER_ENDPOINT` 环境变量

### 高可用

1. **多副本部署**
   - 最少 2 个副本
   - 配置 PodDisruptionBudget

2. **跨可用区部署**
   - 已配置 topologySpreadConstraints
   - Pod 反亲和性确保分散部署

3. **资源限制**
   - 配置合理的 requests 和 limits
   - 避免资源争用

### 备份与恢复

1. **配置备份**
   ```bash
   # 备份 ConfigMap 和 Secrets
   kubectl get configmap lurkbot-config -n lurkbot -o yaml > backup/configmap.yaml
   kubectl get secret lurkbot-secrets -n lurkbot -o yaml > backup/secrets.yaml
   ```

2. **PVC 备份**
   - 使用 Velero 或云提供商的快照功能

---

## 故障排查

### 常见问题

#### Pod 无法启动

```bash
# 查看 Pod 事件
kubectl describe pod -l app.kubernetes.io/name=lurkbot -n lurkbot

# 查看日志
kubectl logs -l app.kubernetes.io/name=lurkbot -n lurkbot --previous
```

#### 健康检查失败

```bash
# 检查端点
kubectl exec -it <pod-name> -n lurkbot -- curl localhost:18789/health

# 检查配置
kubectl exec -it <pod-name> -n lurkbot -- env | grep LURKBOT
```

#### 连接问题

```bash
# 检查服务
kubectl get endpoints lurkbot-gateway -n lurkbot

# 检查网络策略
kubectl get networkpolicy -n lurkbot
```

---

## 参考资料

- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Kubernetes 文档](https://kubernetes.io/docs/)
- [Kustomize 文档](https://kustomize.io/)
