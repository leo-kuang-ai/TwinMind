# Source 与分发边界

- starter_source_commit: `16619432d5918f4d5e0a766edeaefeecab350dc8`
- starter_digest: `53bfd1d643625f7ca8ca593b25736a2e88d2d1ce70a51855e175d222d21fea45`
- distribution_boundary: `public-github-mit`
- license_status: `MIT`
- canonical_source: `skills/bootstrap-second-brain/`
- starter_source: `我的第二大脑/`

此 Skill 采用同目录 `LICENSE` 中的 MIT License。正式 GitHub 源码发布必须在工作树干净后冻结 `release_commit`，并核验 canonical 远端分支 SHA 及该提交中的 LICENSE/SOURCE 文件。独立 ZIP 的 SHA-256 只证明字节一致；未通过 bundle/attestation 双签名、独立渠道 Owner 公钥指纹、预先可信 OpenSSH verifier 和包内容校验的 ZIP，不得跨机器分发或安装。
