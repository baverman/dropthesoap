I had to write some SOAP web services but did not find any good tool.

* soaplib/rpclib. Horrible (really horrible) schema. No any control on
  element order, meaningless wrappers and superfluous types.

* ZSI. Petrified mammoth shit.

* pyws. Suitable for simple tasks only.

So there is the DropTheSoap.

* One-to-one mapping to XSD schema.

* Simple type modeling. You have not to guess how inherit
  your classes. Simply write in XSD notation.

* On-the-fly WSDL generation.