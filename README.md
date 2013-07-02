A Google App Engine application for discovering devices on your home network.

Why on earth do we need an Internet service to find devices on the home network? Well sometimes network topology (e.g. double NAT) and poorly implemented switches and bridges cause UPnP and Bonjour to fail. Also, these protocols are not implemented by Web browsers. This service works with web browsers because it only uses standard HTTP to POST a device location and GET queries to find devices.

