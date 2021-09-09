# Vault Examples

A collection of copy-pastable code example snippets demonstrating the various ways to use the [HashiCorp Vault](https://github.com/hashicorp/vault) client libraries to authenticate and retrieve secrets.

Find the relevant file inside the designated directory for the language of your choice, and paste the example code into your application. (This repo is not intended to be "run" as a standalone application.)

## How To Contribute

If you would like to submit a code example to this repo, please create a file containing one function (or a grouping of several related functions) in the language-appropriate directory.

It may also be worth creating a test that calls the function(s). You can use the environment variable EXPECTED_SECRET_VALUE for comparison in your tests. If you're adding some code in a new language, you will need to do some extra work to add the proper test setup to the CI script, including setting any required environment variables.