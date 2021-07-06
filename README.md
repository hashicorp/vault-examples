# Vault Examples

A collection of example code snippets demonstrating the various ways to use the [HashiCorp Vault](https://github.com/hashicorp/vault) client libraries to retrieve secrets.

## How To Contribute

If you would like to submit a code example to this repo, please create a file containing one function (or a grouping of several related functions) in the language-appropriate directory, then create a test that calls the function(s). You can use the environment variable EXPECTED_SECRET_VALUE for comparison in your tests.

If you're adding some code in a new language, you will need to do some extra work to add the proper test setup to the CI script, including setting any required environment variables.