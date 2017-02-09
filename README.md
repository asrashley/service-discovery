A Google App Engine application for discovering devices on your home network.

Why on earth do we need an Internet service to find devices on the home network? Well sometimes network topology (e.g. double NAT) and poorly implemented switches and bridges cause UPnP and Bonjour to fail. Also, these protocols are not implemented by Web browsers. This service works with web browsers because it only uses standard HTTP to POST a device location and GET queries to find devices.

When an in-home device attempts service discovery, the cloud service queries its database for the list of all of the devices it knows about that share the same external IP address. It then filters this list by the subnet of the home LAN, which removes devices that cannot possibly be on the same LAN. The returned list has the local IP address and a unique ID for each of these potential devices.

The client polls each IP address, using a URL that contains this unique ID. In-home devices only respond to this request if the request includes the devices' ID.
