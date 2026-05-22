#!/bin/bash
# dashboard 코드를 Vercel(stock-platform) 프로덕션에 수동 배포하는 스크립트
# 사용법: 저장소 루트에서 ./deploy.sh 실행
# (데이터 파일은 raw.githubusercontent.com에서 서빙되므로 배포 불필요.
#  이 스크립트는 dashboard/ 코드가 바뀌었을 때만 실행하면 됩니다.)

set -e
cd "$(dirname "$0")"

echo "▶ Vercel 프로덕션 배포 시작 (stock-platform)..."
vercel --prod --yes
echo "✅ 배포 완료. https://stock-platform-five.vercel.app"
