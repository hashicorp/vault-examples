# Vault Examples

A collection of copy-pastable code example snippets demonstrating the various ways to use the Vault client libraries for various languages to authenticate and retrieve secrets.

## How To Use 

Find the relevant file inside the designated directory for the language of your choice, and paste the example code into your application. (This repo is not intended to be "run" as a standalone application.)

### Dotnet
These examples use the community maintained library: [VaultSharp](https://github.com/rajanadar/VaultSharp)

### Go
These examples use the HashiCorp maintained client library: [HashiCorp Vault](https://pkg.go.dev/github.com/hashicorp/vault/api)

## How To Contribute

If you would like to submit a code example to this repo, please create a file containing one function (or a grouping of several related functions) in the language-appropriate directory.

We create the examples as functions so that they may be easily tested. When adding a code example, it may also be worth creating a test that calls the function(s). You can use the environment variable EXPECTED_SECRET_VALUE for comparison in your tests. If you're adding some code in a new language, you will need to do some extra work to add the proper test setup to the CI script, including setting any required environment variables.