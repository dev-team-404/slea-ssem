# npm 설치 방법

## Node.js 공식 저장소 추가용 curl 설치 (없으면)

``` bash
sudo apt update
sudo apt install -y curl
```

## NodeSource Node.js 18.x 버전 저장소 추가 (원하는 버전으로 변경 가능)

``` bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
```

## Node.js와 npm 설치

``` bash
sudo apt install -y nodejs
```

## 설치 확인

``` bash
node -v
npm -v
```

---

## Node.js와 npm 설치가 완료되었다면 아래 명령어로 전역(global)으로 markdownlint-cli를 설치
>
> sudo 권한으로 설치 가능

``` bash
sudo npm install -g markdownlint-cli
```
