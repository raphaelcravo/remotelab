import subprocess
import re
from tabulate import tabulate
import sys

poolint = 'eth1'  # Network card that will be used to create the vlan subinterfaces
poolindex = '1'  # what file will be used. Example: 1 = samples1 , 2 = samples2 and so on


def subprocess_cmd(command):
    try:
        run_command = subprocess.run(command)
    except subprocess.CalledProcessError as shcommand:
        print("error code: ", shcommand.returncode, shcommand.output)
        exit()


def flush_subinterfaces():
    # Function to remove all vlan subinterfaces that may be set on the system, by using NMCLI command to destroy
    # any connection that starts with "vlan-".

    connection_list = subprocess.run(["nmcli", "connection", "show"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True)
    vlan_list = re.findall(r'vlan-\S*', str(connection_list.stdout))
    print("subinterfaces encontradas: ", vlan_list)
    if vlan_list:
        for vlan_subint in vlan_list:
            subprocess_cmd(["nmcli", "connection", "delete", vlan_subint])
            print("Sub-interface da amostra " + vlan_subint + " removida")
    else:
        print("não há sub-interfaces para serem removidas")


def conn_sample(sample_name, mgmt_ip, vlan_id, mode):
    # Creates a vlan subinterface on the system, using the poll interface (poolint) as master device. Then configure
    # ipv4 connection based on mode choice (dhcp or static)

    int_metric = "50"

    subprocess_cmd(["nmcli", "connection", "add", "type", "vlan", "ifname", vlan_id, "dev", poolint, "id", vlan_id,
                    "ipv4.route-metric", int_metric, "ipv6.route-metric", int_metric])

    if mode == 'static':
        # The static IP is defined using the management ip of the sample (mgmt_ip) as reference, then the
        # value of the last octet is changed by adding +30 (or -30 if the result is greater than 254). this works
        # for /24 addresses.

        ip4netadd = mgmt_ip[:mgmt_ip.rfind(".")]
        ip4host_octect = mgmt_ip[mgmt_ip.rfind(".") + 1:]
        if int(ip4host_octect) + 30 < 254:
            ip4 = ip4netadd + "." + str(int(ip4host_octect) + 30)
        else:
            ip4 = ip4netadd + "." + str(int(ip4host_octect) - 30)

        subprocess_cmd(["nmcli", "connection", "modify", "vlan-" + vlan_id, "ipv4.method", "manual", "ipv6.method",
                        "dhcp", "ip4", ip4 + "/24", "gw4", mgmt_ip])
        subprocess_cmd(["nmcli", "device", "connect", vlan_id])

        print("Rede conectada na vlan " + vlan_id + " na interface " + poolint + " com endereço IPv4 estático " + ip4)
        print("\n Acesse a amostra pelo endereço: " + "http://" + mgmt_ip)

    elif mode == "dhcp":
        # Aqui é feito a definição da interface via DHCP com a interface lan da amostra
        command = ["nmcli", "connection", "modify", "vlan-" + vlan_id, "ipv4.method", "auto", "ipv6.method", "auto"]
        subprocess_cmd(command)
        command = ["nmcli", "device", "connect", vlan_id]
        subprocess_cmd(command)
        print("ATENÇÃO - Este método de configuração depende do serviço DHCP da amostra estar habilitado")
        print("Conexão com a amostra configurada na interface: " + poolint + "@" + vlan_id)


def list_and_configure_samples(pool):
    # le o arquivo samples1 ou samples2 (dependendo do valor em pool) e exibe na tela as opções de amostras,
    # além de alimentar a dicionário samplelist com as informações de ip e vlans de cada amostra.

    with open('samples' + str(pool), 'r', encoding='UTF-8') as samplefile:
        samplefile = samplefile.read().splitlines()

    samplelist = []
    sample = []
    show_samplelist = []
    show_samplelist_header = ["OPÇÃO", "NOME_AMOSTRA"]
    option_index = 0

    for line in samplefile:
        line = line.split(' ')
        option_index = option_index + 1
        samplelist.append(
            dict(
                index=str(option_index),
                sample_name=line[0],
                mgmt_ip=line[1],
                vlan_id=line[2]
            )
        )

    print("Lista de amostras:")
    for line in samplelist:
        show_samplelist.append(
            [
                'ID ' + line['index'],
                line['sample_name']
            ]
        )

    print(tabulate(show_samplelist, show_samplelist_header))

    while True:  # Gets and check the sample option
        try:
            selected_option = int(input('\n Digite o ID da amostra ou 0 para deletar todas as sub-interfaces:  '))
        except ValueError:
            print('Opção inválida')
        else:
            if selected_option > len(samplelist) and selected_option != 0:
                print('Opção inválida')
            elif selected_option == 0:
                flush_subinterfaces()
                exit()
            else:
                selected_option = selected_option - 1  # This is for the input to match the list index
                break

    print('\nSelecione o método de configuração: ')
    print("\n1-IP estático\n2-DHCP")

    while True:  # Gets and check the DHCP/STATIC option
        try:
            selected_mode = int(input('\nMétodo de configuração: '))
        except ValueError:
            print('Opção inválida')
        else:
            if selected_mode == 1:
                con_method = "static"
                break
            elif selected_mode == 2:
                con_method = "dhcp"
                break
            else:
                print('método inválido - digite 1 ou 2')

    sample = samplelist[selected_option]
    flush_subinterfaces()
    conn_sample(sample['sample_name'], sample['mgmt_ip'], sample['vlan_id'], con_method)


try:
    if sys.argv[1] == '-c':
        flush_subinterfaces()
except IndexError:
    list_and_configure_samples('1')
