"""Bundled clean-prose corpus for the readability test-bed.

Error-free by construction (field DEC 37434c1e): uniform-register prose,
deliberately salted with confusable words (their/there, its, affect/effect)
and droppable function words so all five seeded error classes bite, and
mechanically scanned by the test suite for pre-existing instances of the
injectable classes (no adjacent duplicate tokens, every class applicable).
Extend only with the same guarantees, never with unproofread text — the
experiment's clean controls depend on it."""

PARAGRAPHS = (
    "A sourdough starter is nothing more than flour and water, left out "
    "until wild yeast settles in. Bakers feed it daily, discarding half "
    "before each meal, and over time its aroma shifts from raw paste to "
    "something sharp and fruity. The dough it leavens rises slowly, which "
    "gives the crumb an open, glossy structure.",
    "Ocean tides follow the pull of the moon more than the sun, though both "
    "matter. Twice a day most coastlines watch the water climb and retreat, "
    "and sailors plan their departures around the change. In narrow bays "
    "the effect is amplified, funneling the swell into differences of "
    "several meters between morning and afternoon.",
    "A cast iron pan improves with use because thin layers of oil "
    "polymerize into a smooth, dark coating. Cooks who scrub theirs with "
    "harsh soap strip that seasoning away, then wonder why eggs cling to "
    "the metal. Restoring the surface takes patience, a hot oven, and "
    "several rounds of careful oiling.",
    "Honeybees communicate the location of food through a dance performed "
    "on the vertical face of the comb. The angle of the run encodes "
    "direction relative to the sun, while its duration signals distance. "
    "Foragers that follow the dance leave the hive and fly a remarkably "
    "accurate line to the flowers.",
    "Glassblowers gather molten glass on the end of a hollow pipe, then "
    "shape it with breath, gravity, and steady rotation. The material "
    "forgives nothing, since it stiffens as it cools and shatters if "
    "chilled too fast. Finished pieces rest overnight in an annealing "
    "oven, where the temperature falls gently enough to relieve internal "
    "stress.",
    "Early mapmakers worked from travelers' accounts, which explains the "
    "sea monsters and distorted coastlines that decorate their charts. A "
    "map is always an argument about what matters, not a neutral picture. "
    "Modern surveys replaced rumor with measurement, yet every projection "
    "still trades one kind of accuracy for another.",
    "Coffee roasting is a race between heat and chemistry. Green beans "
    "smell of grass and hay, but time in the drum turns them fragrant, "
    "brittle, and brown. Roasters listen for the first crack, a popping "
    "sound that marks the moment sugars caramelize, and they pull the "
    "batch seconds later or let it darken further.",
    "Beginning chess players memorize openings, while stronger ones study "
    "endgames first. With only a few pieces on the board, the logic of the "
    "position becomes visible, and there is nowhere to hide a bad plan. "
    "The habits formed there, patience and precise calculation, carry back "
    "into the crowded middle game.",
    "The first railways standardized time itself. Before trains, each town "
    "set its clocks by the local noon, and nobody minded a few minutes of "
    "drift between villages. Timetables made those differences dangerous, "
    "so the companies imposed a single railway time, which the rest of "
    "society eventually adopted.",
    "Wool keeps sheep comfortable in both directions, insulating against "
    "cold while shedding summer heat. The fiber's natural crimp traps "
    "pockets of air, and its surface repels light rain. Knitters prize "
    "breeds whose fleece is long and fine, then spin the staples into yarn "
    "whose strength comes from twist rather than glue.",
    "Photographers talk about light the way sailors talk about weather. "
    "Harsh noon sun flattens faces and burns out detail, while the hour "
    "after dawn wraps everything in long, warm shadows. Learning to see "
    "the difference takes longer than learning the camera, and it matters "
    "more than any lens in the bag.",
    "A river never keeps the shape it is given. Water on the outside of "
    "each bend accelerates and digs at the bank, while the slack inside "
    "drops its load of sand. Over decades the curves migrate across the "
    "valley floor, leaving crescent lakes and buried gravel where the "
    "channel used to run.",
    "In most towns the library's catalog is older than its shelves, since "
    "collections often began as boxes of donated books hauled between "
    "borrowed rooms. The building came later, funded by subscriptions or a "
    "stubborn council, and the librarians then spent years imposing order "
    "on decades of generous chaos.",
    "A cold front announces itself hours ahead. High feathery clouds "
    "thicken and lower, the wind swings around, and the air takes on a "
    "restless, metallic feel. When the front passes, the temperature can "
    "fall ten degrees in minutes, and the sky behind it opens into hard, "
    "rinsed blue.",
    "Fermentation is controlled spoilage, a truce between cooks and "
    "microbes. Salt holds the invaders back long enough for friendly "
    "bacteria to acidify the brine, and from then on the vegetables are "
    "defended by their own sourness. Crocks of kraut and kimchi keep for "
    "months without refrigeration.",
    "An ordinary pencil is a small international project. The graphite may "
    "come from one continent, the cedar from another, and the clay that "
    "stiffens the core from a third. Factories grind, bake, and glue these "
    "ingredients into a tool so cheap that losing one costs less than a "
    "minute of anyone's attention.",
    "Green and black tea come from the same plant, and the difference lies "
    "entirely in what happens after picking. Leaves destined to stay green "
    "are heated quickly to halt oxidation, while black tea is bruised and "
    "left to darken. Between the two sit the oolongs, whose makers stop "
    "the process partway.",
    "Suspension bridges hang their roadways from cables draped between "
    "towers, which converts the deck's weight into tension. The design "
    "spans distances no beam could cross, but it trembles in wind, and "
    "engineers have learned to respect that motion. A deck that flexes "
    "gracefully outlives one that fights every gust.",
    "Deserts are defined by what leaves rather than what arrives, since "
    "evaporation outruns rainfall. Life there budgets water with an "
    "accountant's discipline. Seeds wait years for a storm, then bloom, "
    "set seed, and wither within weeks, and the animals move their entire "
    "days into the cool hours.",
    "Memory behaves less like a recording and more like a retelling. Each "
    "act of recall rebuilds the scene from fragments, and the rebuilt "
    "version quietly replaces the original. This is why confident "
    "witnesses disagree, and why a story polished over many dinners drifts "
    "further from the evening it describes.",
    "Sailing upwind looks impossible until you watch the sail work as a "
    "wing. Air flowing across the curved cloth generates lift, and the "
    "keel converts that sideways force into forward motion. A boat cannot "
    "point straight into the breeze, so crews advance in zigzags, trading "
    "distance for angle.",
    "Museum collections are mostly invisible. For every painting on the "
    "wall, dozens rest in climate-controlled storage, rotated out to "
    "protect pigments from light. Curators describe their galleries as the "
    "tip of an iceberg, and the real work of the institution happens in "
    "basements the public never sees.",
    "Mechanical clocks keep time by interrupting it. An escapement "
    "releases the gear train one tooth at a time, and each release feeds a "
    "little push back to the pendulum. The tick that fills a quiet room is "
    "the sound of that bargain being renewed twice a second.",
    "Limestone caves grow drop by drop, as rainwater picks up carbon "
    "dioxide and dissolves the rock along its joints. Over thousands of "
    "years the seeping water hollows out galleries, then decorates them "
    "with stone icicles. A formation thicker than your arm may be older "
    "than agriculture.",
    "A kite flies by holding its face against the wind at a shallow angle, "
    "deflecting air downward and riding the reaction. The string does more "
    "than tether it, since tension sets the angle of attack. Shorten the "
    "bridle too far and the kite stalls, lengthen it and the kite dives in "
    "loops.",
    "Cheesemaking begins by convincing milk to abandon its liquid form. "
    "Cultures sour it, rennet sets it into a fragile gel, and the curd is "
    "then cut, stirred, and pressed until the whey runs clear. Everything "
    "afterward, from washing rinds to waxing wheels, is a long negotiation "
    "with mold and time.",
    "Experienced hikers pack for the mountain they might meet rather than "
    "the one in the forecast. Weather above the treeline changes faster "
    "than any bulletin, and a warm afternoon can turn to sleet before the "
    "next ridge. The extra layer at the bottom of the pack weighs little "
    "and argues for itself exactly once.",
    "Good soup rewards restraint at the start and generosity at the end. "
    "Onions sweated slowly build a sweet foundation, while a hard boil "
    "early on clouds the broth and dulls the flavor. Season lightly "
    "through the cooking, then adjust at the finish, when reduction has "
    "concentrated everything in the pot.",
    "Migrating birds navigate by more instruments than any cockpit holds. "
    "They read the arc of the sun, the stars, and the magnetic field, and "
    "they check these against remembered coastlines. Young birds inherit "
    "the compass heading, but the map itself is drawn on the first journey "
    "and corrected for life.",
    "Movable type made errors cheap to fix and ideas cheap to multiply. A "
    "compositor could correct a single letter without recarving a whole "
    "block, and a print run of hundreds cost little more than one of "
    "dozens. Pamphlets crossed borders faster than the authorities who "
    "wanted them stopped.",
    "Gardeners learn their soil before they learn their plants. Clay holds "
    "water and nutrients but suffocates roots when compacted, while sand "
    "drains freely and starves them. Most beds need compost more than "
    "fertilizer, since organic matter feeds the soil's own workforce of "
    "worms, fungi, and bacteria.",
    "The power of a telescope depends less on magnification than on the "
    "width of its aperture. A larger mirror gathers more light, and light "
    "is what resolves faint galaxies from the background dark. Amateur "
    "astronomers therefore chase diameter, hauling tubes the size of water "
    "heaters to fields far from town.",
    "Islands run evolutionary experiments that continents would never "
    "approve. Castaway species arrive rarely and at random, then adapt to "
    "empty niches with strange results, from flightless birds to giant "
    "tortoises. The same isolation that breeds these forms leaves them "
    "defenseless when the wider world finally arrives.",
    "Slow practice is the fastest route to a difficult passage. Playing at "
    "half tempo lets the hands learn the geometry without rehearsing "
    "mistakes, and accuracy at low speed converts into fluency far sooner "
    "than repeated stumbling at full speed. Metronomes enforce the honesty "
    "that enthusiasm undermines.",
    "Bakers preheat their ovens with a ferocity that home cooks find "
    "alarming, because the first minutes of baking decide the loaf. Steam "
    "keeps the crust supple while trapped gases expand, giving the bread "
    "its final spring. Once the surface sets, the shape is fixed, whatever "
    "the crumb might have wished.",
    "Valley fog forms on clear, calm nights, when the ground radiates its "
    "heat to the sky and chills the air above it. Cold air drains "
    "downslope and pools, and moisture condenses into a layer that sunrise "
    "burns away from the top down. Drivers meet the densest banks in the "
    "lowest hollows.",
    "A bicycle stays upright through a conversation between rider and "
    "geometry. Small steering corrections move the wheels back under the "
    "center of mass, and the rake of the fork makes many of those "
    "corrections automatic. Riders sense this as balance, though it is "
    "closer to a continuous, well-practiced fall.",
    "Paper archives outlast most digital ones, not because paper is "
    "durable but because it fails slowly and visibly. A water-stained "
    "ledger can still be read, while a corrupted file is simply gone. "
    "Archivists now migrate collections between formats on a schedule, "
    "treating preservation as motion rather than storage.",
    "Lighthouse keepers once trimmed wicks and wound clockwork through the "
    "night, since the great lenses had to revolve on schedule for ships to "
    "identify the light. Automation ended the profession, and the "
    "buildings now keep their vigil alone, flashing patterns to crews who "
    "read them from habit as much as need.",
    "An orchard is a long agreement between a grower and the future. Trees "
    "planted this spring will not repay the labor for years, and the "
    "varieties chosen now decide the harvests of a decade. Pruning looks "
    "brutal to visitors, yet each cut trades wood the tree can spare for "
    "fruit it could not otherwise carry.",
    "Dry stone walls stand without mortar because each stone is placed to "
    "be held by its neighbors. Builders work with the shapes of the "
    "material rather than against them, saving the flattest pieces for the "
    "top course. A well-built wall flexes with frost and settles with the "
    "ground, outlasting fences by a century.",
    "City dwellers who visit a truly dark sky often mistake the Milky Way "
    "for a cloud. The eye needs half an hour to reach full sensitivity, "
    "and every glance at a phone resets the clock. Astronomers guard their "
    "night vision with red lamps and a certain amount of scolding.",
    "Home canning preserves the harvest by sealing it away from air and "
    "then cooking the sealed jars. Acidity decides the method, since "
    "tomatoes and pickles tolerate a boiling bath while low-acid "
    "vegetables demand pressure. The satisfying pop of a cooling lid tells "
    "the kitchen that the vacuum has taken hold.",
    "Handwriting reveals its history in the tools that shaped it. Broad "
    "quills rewarded strokes of varying width, so medieval scripts grew "
    "thick and thin by design, while the steel pen and the ballpoint "
    "flattened those contrasts. The letters of each generation record the "
    "friction between speed and legibility.",
    "Ferry schedules organize island life the way tides organize a harbor. "
    "Shops receive stock on boat days, appointments on the mainland "
    "cluster around the morning crossing, and a missed departure can cost "
    "a whole day. Islanders keep one eye on the weather, since a gale "
    "cancels everything.",
    "A compost pile is a slow fire that never flames. Bacteria oxidize the "
    "same carbon a match would burn, releasing heat that can steam on a "
    "frosty morning. Turning the heap feeds it oxygen, and within a "
    "season, kitchen scraps and autumn leaves become something dark, "
    "crumbly, and sweet-smelling.",
    "Apprenticeship teaches what books cannot hold, the thousand small "
    "judgments that separate adequate work from excellent work. A master "
    "rarely lectures, and instead assigns tasks slightly beyond comfort, "
    "then corrects the result. The lessons transfer through repetition "
    "until the hands know things their owner cannot yet explain.",
    "A loom holds one set of threads under tension so that another can "
    "cross it, and every textile in history is a variation on that "
    "crossing. Pattern lives in which warp threads lift for each pass of "
    "the shuttle. Complex designs were once stored on punched cards, an "
    "idea computing later borrowed whole.",
)
