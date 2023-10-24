import asyncio
import os
import time
from urllib.parse import urljoin, urlparse
import re
from bs4 import BeautifulSoup
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientResponseError
from loguru import logger
from rich.console import Console

regex_list = {
    "Google API Key": r"AIza[0-9A-Za-z\\-_]{35}",
    "Artifactory API Token": r'(?:\s|=|:|^|"|&)AKC[a-zA-Z0-9]{10,}',
    "Cloudinary API Key": r"cloudinary://[0-9]{15}:[0-9A-Za-z]+@[a-z]+",
    "Firebase API Key": r"AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}",
    "LinkedIn API Key": r"(?i)linkedin(.{0,20})?['\"][0-9a-z]{16}['\"]",
    "Email Address": r"(?<=mailto:)[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z.-]+",
    "PGP Private Key Block": r"-----BEGIN PGP PRIVATE KEY BLOCK-----",
    "SSH Private Key": r"-----BEGIN (?:DSA|EC|OPENSSH|RSA) PRIVATE KEY-----",
    "SSH (ssh-ed25519) Public Key": r"ssh-ed25519",
    "Amazon AWS Access Key ID": r"AKIA[0-9A-Z]{16}",
    "Amazon MWS Auth Token": r"amzn\.mws\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    "Authorization Bearer Token": r"bearer [a-zA-Z0-9_\\-\\.=]+",
    "Authorization Basic Credentials": r"basic [a-zA-Z0-9=:_\+\/-]{5,100}",
    "Authorization API Key": r"api[key|_key|\s+]+[a-zA-Z0-9_\-]{5,100}",
    "JWT Token": r"ey[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$",
    "Facebook Access Token": r"EAACEdEose0cBA[0-9A-Za-z]+",
    "Facebook App ID": r"(?i)(facebook|fb)(.{0,20})?['\"][0-9]{13,17}",
    "Google Cloud Platform API Key": r"(?i)\bAIza[0-9A-Za-z\\-_]{35}\b",
    "Google Cloud Platform OAuth Token": r"[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com",
    "Twitter Access Token": r"(?i)twitter.*['|\"][0-9a-z]{35,44}['|\"]",
    "Windows Live API Key": r"(?i)windowslive.*['|\"][0-9a-f]{22}['|\"]",
    "Microsoft API Key": r"(?i)microsoft.*['|\"][0-9a-f]{22}['|\"]",
    "Microsoft Azure Data Explorer (Kusto) API Key": r"fed=.*",
    "YouTube API Key": r"AIza[0-9A-Za-z-_]{35}",
    "Reddit Client ID": r"(?i)reddit(.{0,20})?['\"][0-9a-zA-Z-_]{14}['\"]",
    "Instagram Access Token": r"(?i)instagram(.{0,20})?['\"][0-9a-zA-Z-_]{7}['\"]",
    "Docker Registry Token": r"(?i)docker[^\s]*?['|\"]\w{32,64}['|\"]",
    "GitHub Personal Access Token": r"[a-f0-9]{40}",
    "GitLab Personal Access Token": r"(?i)gitlab.*['|\"]\w{20,40}['|\"]",
    "JIRA API Token": r"(?i)jira.*['|\"]\w{16}['|\"]",
    "Azure Key Vault Secret Identifier": r"https:\/\/[a-z0-9-]+\.vault\.azure\.net\/secrets\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+",
    "Trello API Key": r"(?i)trello.*['|\"]\w{32}['|\"]",
    "Atlassian API Key": r"(?i)atlassian.*['|\"]\w{32}['|\"]",
    "OAuth 2.0 Bearer Token": r"(?i)bearer[^\s]*?['|\"]\w{32,64}['|\"]",
    "Zoom API Key": r"(?i)zoom.*['|\"]\w{22}['|\"]",
    "Shopify API Key": r"(?i)shopify.*['|\"]\w{32}['|\"]",
    "Zendesk API Token": r"(?i)zendesk.*['|\"]\w{40}['|\"]",
    "Square Access Token": r"(?i)square.*['|\"]\w{64}['|\"]",
    "GitLab OAuth Token": r"(?i)gitlab.*['|\"]\w{20,40}['|\"]",
    "Bitbucket OAuth Token": r"(?i)bitbucket.*['|\"]\w{20,40}['|\"]",
    "Discord Bot Token": r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}",
    "Discord OAuth Token": r"(?i)discord.*['|\"]\w{59}['|\"]",
    "NPM Token": r"(?i)npm[_]?token.*['|\"]\w{64}['|\"]",
    "Confluence API Token": r"(?i)confluence.*['|\"]\w{10}['|\"]",
    "CircleCI API Token": r"(?i)circleci.*['|\"]\w{40}['|\"]",
    "Hootsuite API Token": r"(?i)hootsuite.*['|\"]\w{12}['|\"]",
    "Oracle Cloud API Key": r"[a-zA-Z0-9]{64}",
    "Sentry API Key": r"(?i)sentry.*['|\"]\w{32}['|\"]",
    "DigitalOcean API Token": r"([a-f0-9]{64})",
    "Mailjet API Token": r"(\w{32}-\w{13})",
    "Twitch Client ID": r"(?i)twitch(.{0,20})?['\"][0-9a-z]{30}['\"]",
    "Twitch OAuth Token": r"oauth:[a-z0-9]+",
    "Zoom OAuth Token": r"(?i)zoom.*['|\"]\w{60}['|\"]",
    "Shopify OAuth Token": r"(?i)shopify.*['|\"]\w{20}['|\"]",
    "Zendesk OAuth Token": r"(?i)zendesk.*['|\"]\w{20}['|\"]",
    "Salesforce OAuth Token": r"(?i)salesforce.*['|\"]\w{300}['|\"]",
    "Atlassian OAuth Token": r"(?i)atlassian.*['|\"]\w{300}['|\"]",
    "Stripe Connect OAuth Token": r"(?i)stripe.*['|\"]sk_acct_[0-9a-zA-Z]{24}['|\"]",
    "LinkedIn OAuth Token": r"(?i)linkedin.*['|\"]\w{12}['|\"]",
    "Yammer OAuth Token": r"(?i)yammer.*['|\"]\w{48}['|\"]",
    "Medium Integration Token": r"(?i)medium.*['|\"]\w{100}['|\"]",
    "Coinbase OAuth Token": r"(?i)coinbase.*['|\"]\w{45}['|\"]",
    "Microsoft Office 365 API Token": r"(?i)microsoft.*['|\"]\w{360}['|\"]",
    "Pinterest OAuth Token": r"(?i)pinterest.*['|\"]\w{32}['|\"]",
    "Salesforce API Token": r"(?i)salesforce.*['|\"]\w{300}['|\"]",
    "LinkedIn API Token": r"(?i)linkedin.*['|\"]\w{12}['|\"]",
    "Stripe Connect API Token": r"(?i)stripe.*['|\"]rk_acct_[0-9a-zA-Z]{24}['|\"]",
    "Twitch API Token": r"(?i)twitch.*['|\"]\w{30}['|\"]",
    "Yammer API Token": r"(?i)yammer.*['|\"]\w{48}['|\"]",
    "Coinbase API Token": r"(?i)coinbase.*['|\"]\w{45}['|\"]",
    "Facebook App Token": r"(?i)facebook.*['|\"]\w{140}['|\"]",
    "Facebook App Secret": r"(?i)facebook.*['|\"]\w{32}['|\"]",
    "Google Tag Manager Container ID": r"GTM-[A-Z0-9]{6}",
    "Yelp Fusion API Key": r"(?i)yelp.*['|\"]\w{32}['|\"]",
    "GitKraken OAuth Token": r"(?i)gitkraken.*['|\"]\w{64}['|\"]",
    "Dropbox API Token": r"(?i)dropbox.*['|\"]\w{64}['|\"]",
    "Auth0 API Token": r"(?i)auth0.*['|\"]\w{16}['|\"]",
    "Wix API Key": r"(?i)wix.*['|\"]\w{32}['|\"]",
    "Okta API Token": r"(?i)okta.*['|\"]\w{50}['|\"]",
    "Keybase PGP Key": r"(?i)keybase.*['|\"]\w{64}['|\"]",
    "HashiCorp Vault Token": r"(?i)vault.*['|\"]\w{64}['|\"]",
    "Twilio Auth Token": r"(?i)twilio.*['|\"]\w{32}['|\"]",
    "PagerDuty API Key": r"(?i)pagerduty.*['|\"]\w{20}['|\"]",
    "SendGrid API Key": r"(?i)sendgrid.*['|\"]\w{68}['|\"]",
    "Google Analytics Tracking ID": r"UA-\d{4,10}-\d{1,4}",
    "Mixpanel API Key": r"(?i)mixpanel.*['|\"]\w{32}['|\"]",
    "AWS IAM Secret Key": r"(?i)aws.*['|\"]\w{40}['|\"]",
    "AWS Cognito ID Token": r"(?i)cognito.*['|\"]\w{115}['|\"]",
    "AWS Cognito Refresh Token": r"(?i)cognito.*['|\"]\w{110}['|\"]",
    "Apache Kafka API Key": r"(?i)kafka.*['|\"]\w{32}['|\"]",
    "Splunk API Token": r"(?i)splunk.*['|\"]\w{64}['|\"]",
    "Adobe Marketing Cloud API Key": r"(?i)adobe.*['|\"]\w{24}['|\"]",
    "OneLogin API Token": r"(?i)onelogin.*['|\"]\w{40}['|\"]",
    "Auth0 Client Secret": r"(?i)auth0.*['|\"]\w{40}['|\"]",
    "PubNub API Key": r"(?i)pubnub.*['|\"]\w{40}['|\"]",
    "Fortnite Client ID": r"(?i)fortnite.*['|\"]\w{32}['|\"]",
    "Fortnite Client Secret": r"(?i)fortnite.*['|\"]\w{64}['|\"]",
    "Duo API Key": r"(?i)duo.*['|\"]\w{40}['|\"]",
    "Mapbox API Token": r"(?i)mapbox.*['|\"]\w{32}['|\"]",
    "Nordic APIs API Key": r"(?i)nordicapis.*['|\"]\w{24}['|\"]",
    "Stoplight API Key": r"(?i)stoplight.*['|\"]\w{36}['|\"]",
    "42Crunch API Key": r"(?i)42crunch.*['|\"]\w{64}['|\"]",
    "Prometheus API Key": r"(?i)prometheus.*['|\"]\w{16}['|\"]",
    "Imgur Client ID": r"(?i)imgur.*['|\"]\w{12}['|\"]",
    "Clarifai API Key": r"(?i)clarifai.*['|\"]\w{24}['|\"]",
    "Twillio API Key": r"(?i)twillio.*['|\"]\w{32}['|\"]",
    "Quandl API Key": r"(?i)quandl.*['|\"]\w{20}['|\"]",
    "World Weather Online API Key": r"(?i)worldweatheronline.*['|\"]\w{20}['|\"]",
    "Airtable API Key": r"(?i)airtable.*['|\"]\w{40}['|\"]",
    "Bitly Generic Access Token": r"(?i)bitly.*['|\"]\w{40}['|\"]",
    "Dropbox App Key": r"(?i)dropbox.*['|\"]\w{40}['|\"]",
    "Elasticsearch Authentication": r"(?i)elasticsearch.*['|\"]\w{64}['|\"]",
    "Amazon Web Services Access Key": r"(?i)aws.*['|\"]\w{20}['|\"]",
    "JIRA API Key": r"(?i)jira.*['|\"]\w{16}['|\"]",
    "SendinBlue API Key": r"(?i)sendinblue.*['|\"]\w{64}['|\"]",
    "Zoho API Key": r"(?i)zoho.*['|\"]\w{32}['|\"]",
    "SoundCloud API Key": r"(?i)soundcloud.*['|\"]\w{32}['|\"]",
    "Yandex Disk OAuth Token": r"(?i)yandex.*['|\"]\w{52}['|\"]",
    "Asana Access Token": r"(?i)asana.*['|\"]\w{64}['|\"]",
    "Adobe Creative Cloud API Key": r"(?i)adobe.*['|\"]\w{22}['|\"]",
    "Heroku API Key": r"(?i)heroku.*['|\"]\w{32}['|\"]",
    "Digital Ocean Spaces Access Key": r"(?i)digitalocean.*['|\"]\w{20}['|\"]",
    "Buildkite API Token": r"(?i)buildkite.*['|\"]\w{40}['|\"]",
    "Elastic Email API Key": r"(?i)elasticemail.*['|\"]\w{36}['|\"]",
    "OpenWeatherMap API Key": r"(?i)openweathermap.*['|\"]\w{32}['|\"]",
    "Pusher App Key": r"(?i)pusher.*['|\"]\w{64}['|\"]",
    "Twilio API Key": r"(?i)twilio.*['|\"]\w{32}['|\"]",
    "Mandrill API Key": r"(?i)mandrill.*['|\"]\w{42}['|\"]",
    "Intercom API Key": r"(?i)intercom.*['|\"]\w{64}['|\"]",
    "Shopify Storefront Access Token": r"(?i)shopify.*['|\"]\w{35}['|\"]",
    "Vimeo OAuth Token": r"(?i)vimeo.*['|\"]\w{40}['|\"]",
    "Mailgun API Key": r"(?i)mailgun.*['|\"]\w{32}['|\"]",
    "Zendesk OAuth Token": r"(?i)zendesk.*['|\"]\w{40}['|\"]",
    "PubNub API Key": r"(?i)pubnub.*['|\"]\w{32}['|\"]",
    "Twitter API Key": r"(?i)twitter.*['|\"]\w{35,44}['|\"]",
    "Nexmo API Key": r"(?i)nexmo.*['|\"]\w{32}['|\"]",
    "Spotify Client ID": r"(?i)spotify.*['|\"]\w{32}['|\"]",
    "Stripe API Key": r"(?i)stripe.*['|\"]\w{24}['|\"]",
    "Google Maps API Key": r"(?i)google.*['|\"]\w{39}['|\"]",
    "Bit.ly Generic Access Token": r"(?i)bitly.*['|\"]\w{34}['|\"]",
    "Braintree API Key": r"(?i)braintree.*['|\"]\w{32}['|\"]",
    "Coinbase API Key": r"(?i)coinbase.*['|\"]\w{32}['|\"]",
    "Splunk API Key": r"(?i)splunk.*['|\"]\w{64}['|\"]",
    "AWS IAM Access Key": r"(?i)aws.*['|\"]\w{20}['|\"]",
    "AWS IAM Secret Key": r"(?i)aws.*['|\"]\w{40}['|\"]",
    "Twilio API Key": r"(?i)twilio.*['|\"]\w{32}['|\"]",
    "Firebase Cloud Messaging (FCM) Key": r"AAAA[a-zA-Z0-9_-]{140,340}",
    "Basic Authentication": r"Basic\s[A-Za-z0-9_\-]+=*",
    "Bearer Token": r"['|\"]?token['|\"]?\s*[:=]\s*['|\"]?([a-zA-Z0-9-_]+)['|\"]?",
    "API Token": r"['|\"]?api[_]?key['|\"]?\s*[:=]\s*['|\"]?([a-zA-Z0-9-_]+)['|\"]?",
    "Access Token": r"['|\"]?access[_]?token['|\"]?\s*[:=]\s*['|\"]?([a-zA-Z0-9-_]+)['|\"]?",
    "Client ID": r"['|\"]?client[_]?id['|\"]?\s*[:=]\s*['|\"]?([a-zA-Z0-9-_]+)['|\"]?",
    "Client Secret": r"['|\"]?client[_]?secret['|\"]?\s*[:=]\s*['|\"]?([a-zA-Z0-9-_]+)['|\"]?",
    "API Secret": r"['|\"]?api[_]?secret['|\"]?\s*[:=]\s*['|\"]?([a-zA-Z0-9-_]+)['|\"]?",
    "Session Token": r"['|\"]?session[_]?token['|\"]?\s*[:=]\s*['|\"]?([a-zA-Z0-9-_]+)['|\"]?",
    "Refresh Token": r"['|\"]?refresh[_]?token['|\"]?\s*[:=]\s*['|\"]?([a-zA-Z0-9-_]+)['|\"]?",
}

class SecretScanner:
    TEXT_HTML = "text/html"

    def __init__(self):
        self.console = Console()
        self.scanned_urls = set()

    def display_result(self, key, link, matches, js_file=None):
        self.console.print(f"\n[bold green][+] {key} found in {link}[/bold green]")
        if js_file:
            self.console.print(f"[cyan]Found in JavaScript file:[/cyan] {js_file}")
        self.console.print(f"[red]Matches:[/red] {matches}\n")

    def scan_js_content(self, content, link, js_file=None):
        results = []
        for key, pattern in regex_list.items():
            matches = re.findall(pattern, content)
            if matches:
                self.display_result(key, link, matches, js_file=js_file)
                results.append(f"{key} found in {link}: {matches}")
        return results

    async def fetch(self, url, session):
        try:
            async with session.get(url) as response:
                return await response.text()
        except Exception as e:
            self.log_error(f"Error fetching {url}", exception=e)
            return ""

    async def scan_js_links_async(self, links, base_url):
        async with ClientSession() as session:
            tasks = [self.fetch(urljoin(base_url, link), session) for link in links]
            return await asyncio.gather(*tasks)

    def extract_js_links(self, html_content, base_url):
        soup = BeautifulSoup(html_content, "html.parser")
        js_links = set()
        for script in soup.find_all("script"):
            src = script.get("src")
            if src:
                js_links.add(urljoin(base_url, src))
            else:
                self.scan_js_content(script.text, base_url)
        return list(js_links)

    def filter_external_links(self, base_url, links):
        parsed_base_url = urlparse(base_url)
        return [
            link for link in links if parsed_base_url.netloc == urlparse(link).netloc
        ]

    async def crawl_and_scan_all_js(self, url):
        try:
            if url in self.scanned_urls:
                return []

            self.scanned_urls.add(url)

            async with ClientSession() as session:
                response = await session.get(url, timeout=30, allow_redirects=True)
                content_type = response.headers.get("Content-Type", "").lower()

                if self.TEXT_HTML in content_type:
                    html_content = await response.text()
                    js_links = self.extract_js_links(html_content, url)
                    js_links = self.filter_external_links(url, js_links)

                    self.console.print(f"\n[bold]Scanning {url} for sensitive information...[/bold]\n")

                    results = self.scan_js_content(html_content, url)

                    for js_link in js_links:
                        js_content = await self.fetch(js_link, session)
                        js_results = self.scan_js_content(js_content, js_link)
                        results.extend(js_results)

                    return results
                else:
                    self.console.print(f"[yellow]Skipping {url} (Not HTML content)[/yellow]")
                    return []
        except ClientResponseError as e:
            self.log_error(f"Error accessing {url}", exception=e)
            return []
        except Exception as e:
            self.log_error(f"An unexpected error occurred", exception=e)

    def welcome_message(self):
        ascii_art_logo = """
        ██████╗  ██████╗ ███╗   ██╗███╗   ██╗███████╗
        ██╔══██╗██╔═══██╗████╗  ██║████╗  ██║██╔════╝
        ██║  ██║██║   ██║██╔██╗ ██║██╔██╗ ██║███████╗
        ██║  ██║██║   ██║██║╚██╗██║██║╚██╗██║╚════██║
        ██████╔╝╚██████╔╝██║ ╚████║██║ ╚████║███████║
        ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝
        """
        self.console.print(f"[bold magenta]{ascii_art_logo}[/bold magenta]")
        self.console.print("[cyan][bold]Welcome to the Secret Scanner![/bold][/cyan]\n")
        self.console.print(
            "This tool scans JavaScript files for sensitive information."
        )
        self.console.print(
            "It can find API keys, credentials, and other secrets embedded in the"
            " code.\n"
        )

    def scan_complete_message(self):
        self.console.print("[cyan][bold]Scan complete![/bold][/cyan]")
        self.console.print("Thank you for using the Secret Scanner.")

    def save_results(self, results, output_dir="scan_results"):
        if results is None:
            self.console.print("[yellow]No results to save.[/yellow]")
            return

        os.makedirs(output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d%H%M%S")
        output_file = os.path.join(output_dir, f"scan_results_{timestamp}.txt")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                for result in results:
                    f.write(result + "\n")
            self.console.print(f"[cyan]Results saved to {output_file}[/cyan]")
        except Exception as e:
            self.log_error(f"Error saving results to {output_file}", exception=e)

    def log_error(self, message, exception=None):
        if exception is not None:
            logger.error(f"{message}. Exception: {str(exception)}")
        else:
            logger.error(message)

if __name__ == "__main__":
    try:
        scanner = SecretScanner()
        scanner.welcome_message()
        mode = input("Do you want to scan a single website (S) or a list of websites from a file (L)? ").upper()
        if mode == "S":
            start_url = input("Enter the starting URL to scan: ")
            scanner_results = asyncio.run(scanner.crawl_and_scan_all_js(start_url))
            scanner.save_results(scanner_results)
            scanner.scan_complete_message()
        elif mode == "L":
            file_path = input("Enter the path to the text file containing the list of websites: ")
            with open(file_path, "r") as file:
                websites = file.read().splitlines()
            for website in websites:
                scanner_results = asyncio.run(scanner.crawl_and_scan_all_js(website))
                scanner.save_results(scanner_results)
            scanner.scan_complete_message()
        else:
            print("Invalid mode. Please enter 'S' for a single website or 'L' for a list of websites.")
    except Exception as e:
        scanner.log_error(f"An unexpected error occurred", exception=e)
