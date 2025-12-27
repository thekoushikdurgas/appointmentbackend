<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## Deploying Next.js on AWS EC2 with Nginx

Deploying a Next.js application on AWS EC2 with Nginx as a reverse proxy provides a robust and scalable hosting solution. Here's a comprehensive step-by-step guide.[^1][^2][^3]

### Launch and Configure EC2 Instance

Start by creating an EC2 instance in the AWS Console. Select **Ubuntu 22.04 LTS** as the operating system, and choose an instance type based on your needs—**t2.micro** works for testing and small applications (free-tier eligible), while **t3.medium** or larger instances suit production workloads. Configure security groups to allow inbound traffic on ports **22** (SSH), **80** (HTTP), and **443** (HTTPS if you plan to add SSL).[^3][^1]

Connect to your instance using SSH with the key pair you created during setup. Once connected, update the system packages:[^2][^1]

```bash
sudo apt update && sudo apt upgrade -y
```


### Install Node.js and Dependencies

Install Node.js and npm on your EC2 instance. For production deployments, use Node Version Manager (nvm) to install the latest LTS version, or install directly via apt:[^1][^3]

```bash
# Using apt
sudo apt install nodejs npm -y

# Verify installation
node -v
npm -v
```

Next, install **PM2**, a production process manager for Node.js applications that keeps your app running continuously and restarts it automatically if it crashes:[^1]

```bash
sudo npm install -g pm2
```


### Deploy Your Next.js Application

Clone your Next.js repository from GitHub or transfer your code to the EC2 instance:[^2][^1]

```bash
cd ~
git clone https://github.com/yourusername/your-nextjs-app.git
cd your-nextjs-app
```

Install dependencies and build the production version of your application:[^3][^1]

```bash
npm install
npm run build
```

Start your Next.js application using PM2, which will manage the process and ensure it runs continuously:[^1]

```bash
pm2 start npm --name "nextjs-app" -- start
pm2 save
pm2 startup
```

The `pm2 startup` command generates a startup script that automatically starts PM2 and your application when the server reboots. Verify the application is running on port 3000 by checking `pm2 list`.[^1]

### Install and Configure Nginx

Install Nginx to serve as a reverse proxy, handling incoming HTTP requests and forwarding them to your Next.js application:[^2][^3]

```bash
sudo apt install nginx -y
```

Configure Nginx by editing the default site configuration:[^2][^1]

```bash
sudo nano /etc/nginx/sites-available/default
```

Replace the contents with the following configuration:[^2][^1]

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
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

This configuration directs all incoming traffic to your Next.js app running on port 3000, preserving WebSocket connections and forwarding necessary headers. Test the configuration and restart Nginx:[^4][^2]

```bash
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```


### Configure Domain and Access

If you're using a custom domain, point your domain's DNS A record to your EC2 instance's public IP address. For the initial setup or testing, you can access your application directly using the EC2 public IP address.[^1][^2]

To add SSL/HTTPS support later, you can use **Let's Encrypt** with Certbot to obtain free SSL certificates. You can also integrate **Cloudflare CDN** for additional performance optimization and DDoS protection.[^3][^1]

Your Next.js application should now be live and accessible through your domain or EC2 public IP, with PM2 managing the application process and Nginx handling incoming requests.[^3][^2][^1]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://dev.to/duythenight/deploy-nextjs-on-aws-ec2-with-pm2-nginx-and-cloudflare-cdn-b42

[^2]: https://twm.me/beginner-guide-nextjs-aws-ec2-nginx

[^3]: https://www.linkedin.com/pulse/supercharge-your-nextjs-application-deploying-aws-ec2-kalaiselvam-m2ehc

[^4]: https://rutenisraila.com/blog/reverse-proxy-with-next-js-and-nginx

[^5]: https://arxiv.org/pdf/1904.02184.pdf

[^6]: https://arxiv.org/pdf/2311.06962.pdf

[^7]: https://arxiv.org/pdf/2210.01073.pdf

[^8]: http://arxiv.org/pdf/2407.00832.pdf

[^9]: https://arxiv.org/pdf/2212.03332.pdf

[^10]: http://arxiv.org/pdf/2407.12605.pdf

[^11]: http://arxiv.org/pdf/2309.16962.pdf

[^12]: https://arxiv.org/pdf/2502.15534.pdf

[^13]: https://www.reddit.com/r/nextjs/comments/q49dsx/deploy_next_js_on_aws_ec2_server_help/

[^14]: https://www.youtube.com/watch?v=VbfsXYW-MxU

[^15]: https://www.vocso.com/blog/deploying-a-next-js-application-on-aws-step-by-step-guide/

[^16]: https://learnaws.io/blog/deploy-nextjs-on-ec2

[^17]: https://stackoverflow.com/questions/68023453/how-to-deploy-a-next-js-app-on-aws-using-nginx

[^18]: https://nextjs.org/docs/pages/getting-started/deploying

