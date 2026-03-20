# TFM - Encrypted Traffic Metrics

Scripts to extract metadata-based metrics (TLS record sizes, bursts, uplink/downlink, connections) from PCAP/PCAPNG using tshark/pyshark.

## Project Structure

- `src/featuresH2C`: Initial implementations of feature extraction scripts used as contextual groundwork for the final feature extraction pipeline.
- `src/extractMetrics`: Main implementation for feature extraction.

## Notes

The scripts in `featuresH2C` were developed as exploratory and reference implementations to better understand TLS traffic characteristics before integrating them into the final extraction workflow.