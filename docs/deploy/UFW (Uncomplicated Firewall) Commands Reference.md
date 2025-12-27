<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## UFW (Uncomplicated Firewall) Commands Reference

UFW is Ubuntu's default firewall tool that simplifies iptables configuration. Here's a comprehensive guide to UFW commands organized by functionality.[^1]

### Basic Operations

**Enable/Disable UFW**

```bash
sudo ufw enable           # Activate firewall and enable on boot
sudo ufw disable          # Deactivate firewall and remove rules
sudo ufw reload           # Reload configuration without disabling
sudo ufw reset            # Reset to default settings (removes all rules)
```

**Check Status**

```bash
sudo ufw status                  # Show basic firewall status
sudo ufw status verbose          # Show detailed status with default policies
sudo ufw status numbered         # Show rules with numbers for deletion
```


### Default Policies

Set default behavior for incoming, outgoing, and routed traffic:[^2]

```bash
sudo ufw default deny incoming      # Block all incoming (recommended)
sudo ufw default allow outgoing     # Allow all outgoing (recommended)
sudo ufw default deny routed        # Block forwarded traffic

# Alternative actions: allow, deny, or reject
sudo ufw default reject incoming    # Reject with error response
```


### Allow/Deny Traffic

**By Port Number**

```bash
sudo ufw allow 22                   # Allow port 22 (any protocol)
sudo ufw allow 80/tcp               # Allow port 80 TCP only
sudo ufw allow 443/udp              # Allow port 443 UDP only
sudo ufw deny 25                    # Block port 25
```

**By Service Name**

```bash
sudo ufw allow ssh                  # Allow SSH service
sudo ufw allow http                 # Allow HTTP (port 80)
sudo ufw allow https                # Allow HTTPS (port 443)
sudo ufw allow mysql                # Allow MySQL (port 3306)
```

**Port Ranges**

```bash
sudo ufw allow 6000:6007/tcp        # Allow TCP ports 6000-6007
sudo ufw allow 65100:65200/udp      # Allow UDP port range
```

**Multiple Ports (comma-separated)**[^2]

```bash
sudo ufw allow 22,80,443/tcp        # Allow multiple TCP ports
```


### IP Address Rules

**Allow/Deny Specific IP**

```bash
sudo ufw allow from 203.0.113.101              # Allow all from IP
sudo ufw deny from 203.0.113.100               # Block specific IP
sudo ufw allow from 192.168.1.100 to any port 22  # Allow IP to specific port
```

**Subnet/CIDR Notation**[^3]

```bash
sudo ufw allow from 192.168.1.0/24             # Allow entire subnet
sudo ufw deny from 10.0.0.0/8                  # Block network range
sudo ufw allow from 192.168.1.0/24 to any port 3306  # Subnet to specific port
```

**IP with Protocol**

```bash
sudo ufw allow from 203.0.113.101 to any port 22 proto tcp
sudo ufw deny from 192.168.0.1 to any port 80 proto tcp
```


### Interface-Specific Rules

Apply rules to specific network interfaces:[^2]

```bash
sudo ufw allow in on eth0 to any port 80 proto tcp    # Allow HTTP on eth0
sudo ufw allow out on wlan0 to any port 53            # Allow DNS on wlan0
sudo ufw deny in on eth1 from 10.0.0.0/8              # Block subnet on eth1
```


### Rate Limiting (Anti-Brute Force)

Limit connection attempts to prevent brute-force attacks:[^3]

```bash
sudo ufw limit ssh                    # Limit SSH connections (max 6 in 30 sec)
sudo ufw limit 22/tcp                 # Same as above
sudo ufw limit from 192.168.1.0/24 to any port 22  # Limit subnet to SSH
```


### Deleting Rules

**Method 1: By Rule Specification**[^4]

```bash
sudo ufw delete allow 22              # Delete by matching rule
sudo ufw delete deny 80/tcp           # Delete specific deny rule
sudo ufw delete allow from 203.0.113.101  # Delete IP-based rule
```

**Method 2: By Rule Number** (Recommended)[^5][^4]

```bash
sudo ufw status numbered              # List rules with numbers
sudo ufw delete 2                     # Delete rule #2
# You'll be prompted to confirm before deletion
```


### Application Profiles

**List and Manage Application Profiles**

```bash
sudo ufw app list                     # Show available application profiles
sudo ufw app info 'Apache Full'       # Show profile details
sudo ufw allow 'Nginx Full'           # Allow using profile
sudo ufw allow 'OpenSSH'              # Allow SSH via profile
```


### Advanced Examples

**Scenario 1: Web Server Configuration**[^3]

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

**Scenario 2: Block Specific IPs but Allow Others**[^1]

```bash
sudo ufw deny from 192.168.0.1 to any port 22
sudo ufw deny from 192.168.0.7 to any port 22
sudo ufw allow from 192.168.0.0/24 to any port 22 proto tcp
```

**Scenario 3: Allow FTP Services**[^2]

```bash
sudo ufw allow 20/tcp                 # FTP data transfer
sudo ufw allow 21/tcp                 # FTP control
```

**Scenario 4: Database Server**[^2]

```bash
sudo ufw allow from 192.168.1.0/24 to any port 3306  # MySQL from local network
sudo ufw allow from 192.168.1.0/24 to any port 5432  # PostgreSQL from local network
```


### Logging Configuration

Control UFW logging verbosity:

```bash
sudo ufw logging on                   # Enable logging
sudo ufw logging off                  # Disable logging
sudo ufw logging low                  # Low verbosity
sudo ufw logging medium               # Medium verbosity
sudo ufw logging high                 # High verbosity
sudo ufw logging full                 # Maximum verbosity
```

View logs:

```bash
sudo tail -f /var/log/ufw.log         # Monitor UFW logs in real-time
sudo grep UFW /var/log/syslog         # Search system logs for UFW entries
```


### Dry Run (Test Mode)

Test commands without applying them:[^6]

```bash
sudo ufw --dry-run enable             # Test enable without activating
sudo ufw --dry-run allow 80           # Preview rule without adding
```


### Practical Tips

1. **Order Matters**: UFW processes rules from top to bottom, so place more specific rules before general ones[^7]
2. **Always Allow SSH First**: Before enabling UFW, ensure SSH is allowed to avoid locking yourself out
3. **Check Before Enabling**: Review rules with `sudo ufw status numbered` before enabling
4. **IPv6 Support**: UFW handles both IPv4 and IPv6 automatically when enabled in `/etc/default/ufw`
5. **Rate Limiting**: Use `limit` instead of `allow` for SSH to prevent brute-force attacks

These commands provide complete control over your Ubuntu firewall, making it easy to secure your server while maintaining the flexibility needed for various network configurations.[^8][^5][^1]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^9]</span>

<div align="center">⁂</div>

[^1]: https://help.ubuntu.com/community/UFW

[^2]: https://www.zenarmor.com/docs/network-security-tutorials/how-to-set-up-a-firewall-with-ufw-on-ubuntu

[^3]: https://linuxconfig.org/ubuntu-24-04-firewall-a-quick-guide

[^4]: https://linuxize.com/post/how-to-list-and-delete-ufw-firewall-rules/

[^5]: https://www.digitalocean.com/community/tutorials/ufw-essentials-common-firewall-rules-and-commands

[^6]: https://blog.rtsp.us/ufw-uncomplicated-firewall-cheat-sheet-a9fe61933330

[^7]: https://serverstadium.com/knowledge-base/securing-ubuntu-with-ufw/

[^8]: https://documentation.ubuntu.com/server/how-to/security/firewalls/

[^9]: https://www.semanticscholar.org/paper/1ebe273fa27deaed522310d1c18ae1ba5d9d0c29

[^10]: https://www.semanticscholar.org/paper/53c0eb3175fbda219dcc3121843235018e02b7d7

[^11]: https://www.semanticscholar.org/paper/8120bdc61b15780f3f77d4aca8c26c5ed0c65f8b

[^12]: https://link.springer.com/10.1007/978-1-4302-1081-8_12

[^13]: https://www.semanticscholar.org/paper/db81c2888e68d847916d16833ba30cc3cab687b6

[^14]: https://www.semanticscholar.org/paper/a5424853e067d1fab67665b42bb7058a2c07aeaf

[^15]: https://dl.acm.org/doi/10.1145/3017680.3017839

[^16]: https://dl.acm.org/doi/10.1145/2839509.2844712

[^17]: https://serverspace.io/support/help/basic-commands-ufw/

[^18]: https://www.itprotoday.com/linux-os/linux-ufw-uncomplicated-firewall-configuration-made-easy

