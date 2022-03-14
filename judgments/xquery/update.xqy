xquery version "1.0-ml";

import module namespace xdmp = "http://marklogic.com/xdmp" at "/MarkLogic/appservices/xdmp/xdmp.xqy";
declare namespace akn = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0";
declare namespace uk = "https://caselaw.nationalarchives.gov.uk";

declare variable $uri as xs:string? external;
declare variable $published as xs:boolean? external;

let $props := ( <published>$published</published> )

return xdmp:document-set-properties($uri, $props)
