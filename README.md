# TFM - Encrypted Traffic Metrics

Scripts to extract metadata-based metrics (TLS record sizes, bursts, uplink/downlink, connections) from PCAP/PCAPNG using tshark/pyshark.

## Project Structure

- `src/featuresH2C`: Initial implementations of feature extraction scripts used as contextual groundwork for the final feature extraction pipeline.
- `src/extractMetrics`: Main implementation for feature extraction.

## Feature Vector

The script `src/extractMetrics` generates a fixed-length feature vector representing TLS traffic characteristics extracted from PCAP files.

The vector is structure as follows:

[0] ---------- incoming TLS records ------------------------ (a) Connection stats  
[1] ---------- outgoing TLS records  
[2] ---------- total TLS bytes   

[3..7] ------- min/max/std/mean/median (method 1) ---------- (b) Burst method 1  

[8..12] ------ min/max/std/mean/median (blocks of 20) ------ (b) Burst method 2  

[13] --------- distinct incoming sizes --------------------- (c) Count diff sizes  
[14] --------- distinct outgoing sizes                    

[15..34] ----- 20 least frequent incoming sizes ------------ (d) Top 20 Diff sizes incoming 
[35..54] ----- 20 least frequent outgoing sizes ------------ (d) Top 20 Diff sizes outgoing

[55..18486] -- frequency per incoming size [1..18432] ------ (e) Freq. per incoming size
[18487..36918] frequency per outgoing size [1..18432] ------ (e) Freq. per outgoing size

Total features: 3 + 5 + 5 + 2 + 20 + 20 + 18432 + 18432 = 36,919

## Notes

The scripts in `featuresH2C` were developed as exploratory and reference implementations to better understand TLS traffic characteristics before integrating them into the final extraction workflow.