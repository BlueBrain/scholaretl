# Application Setup

If one wants to run the application locally, it is needed to setup some environment variables first through
the CLI or an `.env` file.

## Optional environment variables

Here is the list of environment variables that can be set up:

### Related to Grobid

To be able to use the endpoint `/parse/grobid_pdf`, it is needed to setup the environment variable
`SCHOLARETL__GROBID__URL`. 

#### Related to the logging

   - `SCHOLARETL__LOGGING__LEVEL`: the logging level of the application and the `scholaretl` package logging. By default, the value is `info`.
   - `SCHOLARETL__LOGGING__EXTERNAL_PACKAGES`: the logging level of the external packages. By default, the value is `warning`.
