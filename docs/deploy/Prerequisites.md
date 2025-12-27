<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## Prerequisites

Before deploying your Next.js application on EC2, ensure you have an **Ubuntu 22.04 LTS** EC2 instance running with security groups allowing HTTP (port 80) and HTTPS (port 443) traffic. SSH access should be configured for server management.[^1][^2][^3]

## Install Dependencies

Connect to your EC2 instance via SSH and install Node.js and Nginx:[^2][^1]

```bash
sudo apt update
sudo apt install -y nginx
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

Install **PM2** globally to manage your Next.js process:[^3][^1]

```bash
sudo npm install -g pm2
```


## Deploy Your Application

Navigate to your project directory and clone your repository:[^1][^2]

```bash
cd ~
git clone https://github.com/yourusername/your-nextjs-app.git
cd your-nextjs-app
```

Install dependencies and build the production bundle:[^2][^1]

```bash
npm install
npm run build
```

Start your Next.js application with PM2 on port 3000:[^4][^1]

```bash
pm2 start npm --name "nextjs-app" -- start
pm2 save
pm2 startup
```

The `pm2 startup` command ensures your application restarts automatically after server reboots.[^5]

## Configure Nginx Reverse Proxy

Open the default Nginx configuration file:[^6][^1]

```bash
sudo nano /etc/nginx/sites-available/default
```

Replace the contents with the following configuration:[^6][^1]

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Test the Nginx configuration for syntax errors and restart the service:[^7][^1]

```bash
sudo nginx -t
sudo systemctl restart nginx
```


## Verify Deployment

Your Next.js application should now be accessible via your domain or EC2 public IP address. Nginx acts as a reverse proxy, forwarding requests from port 80 to your Next.js application running on port 3000. PM2 ensures the application runs continuously and restarts automatically if it crashes.[^8][^3][^4][^5][^1][^6]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^9]</span>

<div align="center">⁂</div>

[^1]: https://dev.to/duythenight/deploy-nextjs-on-aws-ec2-with-pm2-nginx-and-cloudflare-cdn-b42

[^2]: https://www.linkedin.com/pulse/supercharge-your-nextjs-application-deploying-aws-ec2-kalaiselvam-m2ehc

[^3]: https://twm.me/beginner-guide-nextjs-aws-ec2-nginx

[^4]: https://learnaws.io/blog/deploy-nextjs-on-ec2

[^5]: https://episyche.com/blog/user-guide-for-deploying-the-nextjs-app-in-production-using-pm2-and-nginx

[^6]: https://stackoverflow.com/questions/64386737/how-to-deploy-nextjs-with-nginx

[^7]: https://rutenisraila.com/blog/reverse-proxy-with-next-js-and-nginx

[^8]: https://blog.stackademic.com/nginx-for-deploying-next-js-application-on-aws-ec2-with-aws-elb-control-and-stability-of-a99185deb1c6

[^9]: https://www.ijfmr.com/papers/2023/6/11371.pdf

[^10]: https://arxiv.org/pdf/2210.01073.pdf

[^11]: https://arxiv.org/pdf/1904.02184.pdf

[^12]: https://arxiv.org/pdf/1905.07314.pdf

[^13]: http://arxiv.org/pdf/2405.21009.pdf

[^14]: http://arxiv.org/pdf/2012.10526.pdf

[^15]: https://arxiv.org/pdf/2311.06962.pdf

[^16]: https://academic.oup.com/bioinformatics/advance-article-pdf/doi/10.1093/bioinformatics/btae486/58749467/btae486.pdf

[^17]: https://www.vocso.com/blog/deploying-a-next-js-application-on-aws-step-by-step-guide/

[^18]: https://nextjs.org/docs/pages/getting-started/deploying

