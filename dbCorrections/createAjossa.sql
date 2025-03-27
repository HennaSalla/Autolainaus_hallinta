-- DROP VIEW public.ajossa;
-- View: public.ajossa

-- DROP VIEW public.ajossa;

CREATE OR REPLACE VIEW public.ajossa
 AS
 SELECT lainaus.rekisterinumero,
 	merkki,
	malli,
	auto.automaatti,
	henkilomaara,
        (lainaaja.etunimi::text || ' '::text) || lainaaja.sukunimi::text AS kuljettaja
   FROM lainaaja
     INNER JOIN lainaus ON lainaaja.hetu = lainaus.hetu
     INNER JOIN auto ON lainaus.rekisterinumero = auto.rekisterinumero
   WHERE lainaus.palautus IS NULL;

ALTER TABLE public.ajossa
    OWNER TO postgres;

GRANT SELECT ON VIEW public.ajossa TO autolainaus;
GRANT ALL ON VIEW public.ajossa TO postgres;